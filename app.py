import os
import re
import random
from scipy.io.wavfile import write
from scipy.io.wavfile import read
import numpy as np
import gradio as gr
import yt_dlp
import subprocess
import sys
from argparse import ArgumentParser
from tabs.settings import select_themes_tab
from assets.i18n.i18n import I18nAuto
i18n = I18nAuto()

import assets.themes.loadThemes as loadThemes

if __name__ == "__main__":
   parser = ArgumentParser(description="Separate audio into multiple stems")
   parser.add_argument("--share", action="store_true", dest="share_enabled", default=False, help="Enable sharing")
   parser.add_argument('--listen-port', type=int, help="The listening port that the server will use.")
   args = parser.parse_args()

roformer_models = {
        'BS-Roformer-Viperx-1297.ckpt': 'model_bs_roformer_ep_317_sdr_12.9755.ckpt',
        'BS-Roformer-Viperx-1296.ckpt': 'model_bs_roformer_ep_368_sdr_12.9628.ckpt',
        'BS-Roformer-Viperx-1053.ckpt': 'model_bs_roformer_ep_937_sdr_10.5309.ckpt',
        'Mel-Roformer-Viperx-1143.ckpt': 'model_mel_band_roformer_ep_3005_sdr_11.4360.ckpt'
}

mdx23c_models = [
    'MDX23C_D1581.ckpt',
    'MDX23C-8KFFT-InstVoc_HQ.ckpt',
    'MDX23C-8KFFT-InstVoc_HQ_2.ckpt',
]

mdxnet_models = [
    'UVR-MDX-NET-Inst_full_292.onnx',
    'UVR-MDX-NET_Inst_187_beta.onnx',
    'UVR-MDX-NET_Inst_82_beta.onnx',
    'UVR-MDX-NET_Inst_90_beta.onnx',
    'UVR-MDX-NET_Main_340.onnx',
    'UVR-MDX-NET_Main_390.onnx',
    'UVR-MDX-NET_Main_406.onnx',
    'UVR-MDX-NET_Main_427.onnx',
    'UVR-MDX-NET_Main_438.onnx',
    'UVR-MDX-NET-Inst_HQ_1.onnx',
    'UVR-MDX-NET-Inst_HQ_2.onnx',
    'UVR-MDX-NET-Inst_HQ_3.onnx',
    'UVR-MDX-NET-Inst_HQ_4.onnx',
    'UVR_MDXNET_Main.onnx',
    'UVR-MDX-NET-Inst_Main.onnx',
    'UVR_MDXNET_1_9703.onnx',
    'UVR_MDXNET_2_9682.onnx',
    'UVR_MDXNET_3_9662.onnx',
    'UVR-MDX-NET-Inst_1.onnx',
    'UVR-MDX-NET-Inst_2.onnx',
    'UVR-MDX-NET-Inst_3.onnx',
    'UVR_MDXNET_KARA.onnx',
    'UVR_MDXNET_KARA_2.onnx',
    'UVR_MDXNET_9482.onnx',
    'UVR-MDX-NET-Voc_FT.onnx',
    'Kim_Vocal_1.onnx',
    'Kim_Vocal_2.onnx',
    'Kim_Inst.onnx',
    'Reverb_HQ_By_FoxJoy.onnx',
    'UVR-MDX-NET_Crowd_HQ_1.onnx',
    'kuielab_a_vocals.onnx',
    'kuielab_a_other.onnx',
    'kuielab_a_bass.onnx',
    'kuielab_a_drums.onnx',
    'kuielab_b_vocals.onnx',
    'kuielab_b_other.onnx',
    'kuielab_b_bass.onnx',
    'kuielab_b_drums.onnx',
]

vrarch_models = [
    '1_HP-UVR.pth',
    '2_HP-UVR.pth',
    '3_HP-Vocal-UVR.pth',
    '4_HP-Vocal-UVR.pth',
    '5_HP-Karaoke-UVR.pth',
    '6_HP-Karaoke-UVR.pth',
    '7_HP2-UVR.pth',
    '8_HP2-UVR.pth',
    '9_HP2-UVR.pth',
    '10_SP-UVR-2B-32000-1.pth',
    '11_SP-UVR-2B-32000-2.pth',
    '12_SP-UVR-3B-44100.pth',
    '13_SP-UVR-4B-44100-1.pth',
    '14_SP-UVR-4B-44100-2.pth',
    '15_SP-UVR-MID-44100-1.pth',
    '16_SP-UVR-MID-44100-2.pth',
    '17_HP-Wind_Inst-UVR.pth',
    'UVR-De-Echo-Aggressive.pth',
    'UVR-De-Echo-Normal.pth',
    'UVR-DeEcho-DeReverb.pth',
    'UVR-DeNoise-Lite.pth',
    'UVR-DeNoise.pth',
    'UVR-BVE-4B_SN-44100-1.pth',
    'MGM_HIGHEND_v4.pth',
    'MGM_LOWEND_A_v4.pth',
    'MGM_LOWEND_B_v4.pth',
    'MGM_MAIN_v4.pth',
]

demucs_models = [
    'htdemucs_ft.yaml', 
    'htdemucs.yaml',
    'hdemucs_mmi.yaml',
]

output_format = [
    'wav',
    'flac',
    'mp3',
]

mdxnet_overlap_values = [
    '0.25',
    '0.5',
    '0.75',
    '0.99',
]

vrarch_window_size_values = [
    '320',
    '512',
    '1024',
]

demucs_overlap_values = [
    '0.25',
    '0.50',
    '0.75',
    '0.99',
]

def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'ytdl/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info_dict).rsplit('.', 1)[0] + '.wav'
        sample_rate, audio_data = read(file_path)
        audio_array = np.asarray(audio_data, dtype=np.int16)

        return sample_rate, audio_array

def roformer_separator(roformer_audio, roformer_model, roformer_output_format, roformer_overlap, roformer_segment_size):
  files_list = []
  files_list.clear()
  directory = "./outputs"
  random_id = str(random.randint(10000, 99999))
  pattern = f"{random_id}"
  os.makedirs("outputs", exist_ok=True)
  write(f'{random_id}.wav', roformer_audio[0], roformer_audio[1])
  full_roformer_model = roformer_models[roformer_model]
  prompt = f"audio-separator {random_id}.wav --model_filename {full_roformer_model} --output_dir=./outputs --output_format={roformer_output_format} --normalization=0.9 --mdxc_overlap={roformer_overlap} --mdxc_segment_size={roformer_segment_size}"
  os.system(prompt)

  for file in os.listdir(directory):
    if re.search(pattern, file):
      files_list.append(os.path.join(directory, file))

  stem1_file = files_list[0]
  stem2_file = files_list[1]

  return stem1_file, stem2_file

def mdxc_separator(mdx23c_audio, mdx23c_model, mdx23c_output_format, mdx23c_segment_size, mdx23c_overlap, mdx23c_denoise):
  files_list = []
  files_list.clear()
  directory = "./outputs"
  random_id = str(random.randint(10000, 99999))
  pattern = f"{random_id}"
  os.makedirs("outputs", exist_ok=True)
  write(f'{random_id}.wav', mdx23c_audio[0], mdx23c_audio[1])
  prompt = f"audio-separator {random_id}.wav --model_filename {mdx23c_model} --output_dir=./outputs --output_format={mdx23c_output_format} --normalization=0.9 --mdxc_segment_size={mdx23c_segment_size} --mdxc_overlap={mdx23c_overlap}"
  
  if mdx23c_denoise:
    prompt += " --mdx_enable_denoise"
  
  os.system(prompt)

  for file in os.listdir(directory):
    if re.search(pattern, file):
      files_list.append(os.path.join(directory, file))

  stem1_file = files_list[0]
  stem2_file = files_list[1]

  return stem1_file, stem2_file

def mdxnet_separator(mdxnet_audio, mdxnet_model, mdxnet_output_format, mdxnet_segment_size, mdxnet_overlap, mdxnet_denoise):
  files_list = []
  files_list.clear()
  directory = "./outputs"
  random_id = str(random.randint(10000, 99999))
  pattern = f"{random_id}"
  os.makedirs("outputs", exist_ok=True)
  write(f'{random_id}.wav', mdxnet_audio[0], mdxnet_audio[1])
  prompt = f"audio-separator {random_id}.wav --model_filename {mdxnet_model} --output_dir=./outputs --output_format={mdxnet_output_format} --normalization=0.9 --mdx_segment_size={mdxnet_segment_size} --mdx_overlap={mdxnet_overlap}"
  
  if mdxnet_denoise:
    prompt += " --mdx_enable_denoise"
  
  os.system(prompt)

  for file in os.listdir(directory):
    if re.search(pattern, file):
      files_list.append(os.path.join(directory, file))

  stem1_file = files_list[0]
  stem2_file = files_list[1]

  return stem1_file, stem2_file

def vrarch_separator(vrarch_audio, vrarch_model, vrarch_output_format, vrarch_window_size, vrarch_agression, vrarch_tta, vrarch_high_end_process):
  files_list = []
  files_list.clear()
  directory = "./outputs"
  random_id = str(random.randint(10000, 99999))
  pattern = f"{random_id}"
  os.makedirs("outputs", exist_ok=True)
  write(f'{random_id}.wav', vrarch_audio[0], vrarch_audio[1])
  prompt = f"audio-separator {random_id}.wav --model_filename {vrarch_model} --output_dir=./outputs --output_format={vrarch_output_format} --normalization=0.9 --vr_window_size={vrarch_window_size} --vr_aggression={vrarch_agression}"
  
  if vrarch_tta:
    prompt += " --vr_enable_tta"
  if vrarch_high_end_process:
    prompt += " --vr_high_end_process"

  os.system(prompt)

  for file in os.listdir(directory):
    if re.search(pattern, file):
      files_list.append(os.path.join(directory, file))

  stem1_file = files_list[0]
  stem2_file = files_list[1]

  return stem1_file, stem2_file

def demucs_separator(demucs_audio, demucs_model, demucs_output_format, demucs_shifts, demucs_overlap):
  files_list = []
  files_list.clear()
  directory = "./outputs"
  random_id = str(random.randint(10000, 99999))
  pattern = f"{random_id}"
  os.makedirs("outputs", exist_ok=True)
  write(f'{random_id}.wav', demucs_audio[0], demucs_audio[1])
  prompt = f"audio-separator {random_id}.wav --model_filename {demucs_model} --output_dir=./outputs --output_format={demucs_output_format} --normalization=0.9 --demucs_shifts={demucs_shifts} --demucs_overlap={demucs_overlap}"

  os.system(prompt)

  for file in os.listdir(directory):
    if re.search(pattern, file):
      files_list.append(os.path.join(directory, file))

  stem1_file = files_list[0]
  stem2_file = files_list[1]
  stem3_file = files_list[2]
  stem4_file = files_list[3]

  return stem1_file, stem2_file, stem3_file, stem4_file

def roformer_batch(path_input, path_output, model, output_format, overlap, segment_size):
  found_files = []
  logs = []
  logs.clear()

  extensions = (".mp3", ".wav", ".flac")

  full_roformer_model = roformer_models[model]

  for audio_files in os.listdir(path_input):
    if audio_files.endswith(extensions):
      found_files.append(audio_files)
  total_files = len(found_files)

  if total_files == 0:
    logs.append("No valid audio files.")
    yield "\n".join(logs)
  else:
    logs.append(f"{total_files} audio files found")
    found_files.sort()

    for audio_files in found_files:
      file_path = os.path.join(path_input, audio_files)
      prompt = ["audio-separator", file_path, "-m", f"{full_roformer_model}", f"--output_dir={path_output}", f"--output_format={output_format}", "--normalization=0.9", f"--mdxc_overlap={overlap}", f"--mdxc_segment_size={segment_size}"]
      logs.append(f"Processing file: {audio_files}")
      yield "\n".join(logs)
      subprocess.run(prompt)
      logs.append(f"File: {audio_files} processed!")
      yield "\n".join(logs)

def mdx23c_batch(path_input, path_output, model, output_format, overlap, segment_size, denoise):
  found_files = []
  logs = []
  logs.clear()

  extensions = (".mp3", ".wav", ".flac")

  for audio_files in os.listdir(path_input):
    if audio_files.endswith(extensions):
      found_files.append(audio_files)
  total_files = len(found_files)

  if total_files == 0:
    logs.append("No valid audio files.")
    yield "\n".join(logs)
  else:
    logs.append(f"{total_files} audio files found")
    found_files.sort()

    for audio_files in found_files:
      file_path = os.path.join(path_input, audio_files)
      prompt = ["audio-separator", file_path, "-m", f"{model}", f"--output_dir={path_output}", f"--output_format={output_format}", "--normalization=0.9", f"--mdxc_overlap={overlap}", f"--mdxc_segment_size={segment_size}"]

      if denoise:
        prompt.append("--mdx_enable_denoise")

      logs.append(f"Processing file: {audio_files}")
      yield "\n".join(logs)
      subprocess.run(prompt)
      logs.append(f"File: {audio_files} processed!")
      yield "\n".join(logs)

def mdxnet_batch(path_input, path_output, model, output_format, overlap, segment_size, denoise):
  found_files = []
  logs = []
  logs.clear()

  extensions = (".mp3", ".wav", ".flac")

  for audio_files in os.listdir(path_input):
    if audio_files.endswith(extensions):
      found_files.append(audio_files)
  total_files = len(found_files)

  if total_files == 0:
    logs.append("No valid audio files.")
    yield "\n".join(logs)
  else:
    logs.append(f"{total_files} audio files found")
    found_files.sort()

    for audio_files in found_files:
      file_path = os.path.join(path_input, audio_files)
      prompt = ["audio-separator", file_path, "-m", f"{model}", f"--output_dir={path_output}", f"--output_format={output_format}", "--normalization=0.9", f"--mdx_overlap={overlap}", f"--mdx_segment_size={segment_size}"]

      if denoise:
        prompt.append("--mdx_enable_denoise")

      logs.append(f"Processing file: {audio_files}")
      yield "\n".join(logs)
      subprocess.run(prompt)
      logs.append(f"File: {audio_files} processed!")
      yield "\n".join(logs)

def vrarch_batch(path_input, path_output, model, output_format, window_size, agression, tta, high_end_process):
  found_files = []
  logs = []
  logs.clear()

  extensions = (".mp3", ".wav", ".flac")

  for audio_files in os.listdir(path_input):
    if audio_files.endswith(extensions):
      found_files.append(audio_files)
  total_files = len(found_files)

  if total_files == 0:
    logs.append("No valid audio files.")
    yield "\n".join(logs)
  else:
    logs.append(f"{total_files} audio files found")
    found_files.sort()

    for audio_files in found_files:
      file_path = os.path.join(path_input, audio_files)
      prompt = ["audio-separator", file_path, "-m", f"{model}", f"--output_dir={path_output}", f"--output_format={output_format}", "--normalization=0.9", f"--vr_window_size={window_size}", f"--vr_aggression={agression}"]

      if tta:
        prompt.append("--vr_enable_tta")
      if high_end_process:
         prompt.append("--vr_high_end_process")

      logs.append(f"Processing file: {audio_files}")
      yield "\n".join(logs)
      subprocess.run(prompt)
      logs.append(f"File: {audio_files} processed!")
      yield "\n".join(logs)

def demucs_batch(path_input, path_output, model, output_format, shifts, overlap):
  found_files = []
  logs = []
  logs.clear()

  extensions = (".mp3", ".wav", ".flac")

  for audio_files in os.listdir(path_input):
    if audio_files.endswith(extensions):
      found_files.append(audio_files)
  total_files = len(found_files)

  if total_files == 0:
    logs.append("No valid audio files.")
    yield "\n".join(logs)
  else:
    logs.append(f"{total_files} audio files found")
    found_files.sort()

    for audio_files in found_files:
      file_path = os.path.join(path_input, audio_files)
      prompt = ["audio-separator", file_path, "-m", f"{model}", f"--output_dir={path_output}", f"--output_format={output_format}", "--normalization=0.9", f"--demucs_shifts={shifts}", f"--demucs_overlap={overlap}"]

      logs.append(f"Processing file: {audio_files}")
      yield "\n".join(logs)
      subprocess.run(prompt)
      logs.append(f"File: {audio_files} processed!")
      yield "\n".join(logs)

def select_themes_tab():
    themes_select = gr.Dropdown(
        choices=loadThemes.get_list(),
        value=loadThemes.read_json(),
        label=i18n("Theme"),
        info=i18n(
            "Select the theme you want to use. (Requires restarting the App)"
        ),
        visible=True,
    )
    themes_select.change(
        fn=loadThemes.select_theme,
        inputs=themes_select,
        outputs=[],
    )


with gr.Blocks(theme= loadThemes.load_json() or "NoCrypt/miku", title="🎵 UVR5 UI 🎵") as app:
    gr.Markdown("<h1> 🎵 UVR5 UI 🎵 </h1>")
    gr.Markdown("If you like UVR5 UI you can star my repo on [GitHub](https://github.com/Eddycrack864/UVR5-UI)")
    gr.Markdown("Try UVR5 UI on Hugging Face with A100 [here](https://huggingface.co/spaces/TheStinger/UVR5_UI)")
    with gr.Tabs():

        with gr.TabItem("BS/Mel Roformer"):
            with gr.Row():
                roformer_model = gr.Dropdown(
                    label = "Select the Model",
                    choices=list(roformer_models.keys()),
                    interactive = True
                )
                roformer_output_format = gr.Dropdown(
                    label = "Select the Output Format",
                    choices = output_format,
                    interactive = True
                )
            with gr.Row():
                roformer_overlap = gr.Slider(
                    minimum = 2,
                    maximum = 4,
                    step = 1,
                    label = "Overlap",
                    info = "Amount of overlap between prediction windows.",
                    value = 4,
                    interactive = True
                )
                roformer_segment_size = gr.Slider(
                    minimum = 32,
                    maximum = 4000,
                    step = 32,
                    label = "Segment Size",
                    info = "Larger consumes more resources, but may give better results.",
                    value = 256,
                    interactive = True
                )
            with gr.Row():
                roformer_audio = gr.Audio(
                    label = "Input Audio",
                    type = "numpy",
                    interactive = True
                )
            with gr.Accordion("Separation by Link", open = False):
                with gr.Row():
                    roformer_link = gr.Textbox(
                    label = "Link",
                    placeholder = "Paste the link here",
                    interactive = True
                )
                with gr.Row():
                   gr.Markdown("You can paste the link to the video/audio from many sites, check the complete list [here](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)")
                with gr.Row():
                    roformer_download_button = gr.Button(
                    "Download!",
                    variant = "primary"
                )

            roformer_download_button.click(download_audio, [roformer_link], [roformer_audio])

            with gr.Accordion("Batch Separation", open = False):
                with gr.Row():
                    roformer_input_path = gr.Textbox(
                        label = "Input Path",
                        placeholder = "Place the input path here",
                        interactive = True
                    )
                    roformer_output_path = gr.Textbox(
                        label = "Output Path",
                        placeholder = "Place the output path here",
                        interactive = True
                    )
                with gr.Row():
                    roformer_bath_button = gr.Button("Separate!", variant = "primary")
                with gr.Row():
                    roformer_info = gr.Textbox(
                        label = "Output Information",
                        interactive = False
                    )

            roformer_bath_button.click(roformer_batch, [roformer_input_path, roformer_output_path, roformer_model, roformer_output_format, roformer_overlap, roformer_segment_size], [roformer_info])

            with gr.Row():
                roformer_button = gr.Button("Separate!", variant = "primary")
            with gr.Row():
                roformer_stem1 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    label = "Stem 1",
                    type = "filepath"
                )
                roformer_stem2 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    label = "Stem 2",
                    type = "filepath"
                )

            roformer_button.click(roformer_separator, [roformer_audio, roformer_model, roformer_output_format, roformer_overlap, roformer_segment_size], [roformer_stem1, roformer_stem2])
        
        with gr.TabItem("MDX23C"):
            with gr.Row():
                mdx23c_model = gr.Dropdown(
                    label = "Select the Model",
                    choices = mdx23c_models,
                    interactive = True
                )
                mdx23c_output_format = gr.Dropdown(
                    label = "Select the Output Format",
                    choices = output_format,
                    interactive = True
                )
            with gr.Row():
                mdx23c_segment_size = gr.Slider(
                    minimum = 32,
                    maximum = 4000,
                    step = 32,
                    label = "Segment Size",
                    info = "Larger consumes more resources, but may give better results.",
                    value = 256,
                    interactive = True
                )
                mdx23c_overlap = gr.Slider(
                    minimum = 2,
                    maximum = 50,
                    step = 1,
                    label = "Overlap",
                    info = "Amount of overlap between prediction windows.",
                    value = 8,
                    interactive = True
                )
                mdx23c_denoise = gr.Checkbox(
                    label = "Denoise",
                    info = "Enable denoising during separation.",
                    value = False,
                    interactive = True
                )
            with gr.Row():
                mdx23c_audio = gr.Audio(
                    label = "Input Audio",
                    type = "numpy",
                    interactive = True
                )
            with gr.Accordion("Separation by Link", open = False):
                with gr.Row():
                    mdx23c_link = gr.Textbox(
                    label = "Link",
                    placeholder = "Paste the link here",
                    interactive = True
                )
                with gr.Row():
                   gr.Markdown("You can paste the link to the video/audio from many sites, check the complete list [here](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)")
                with gr.Row():
                    mdx23c_download_button = gr.Button(
                    "Download!",
                    variant = "primary"
                )

            mdx23c_download_button.click(download_audio, [mdx23c_link], [mdx23c_audio])

            with gr.Accordion("Batch Separation", open = False):
                with gr.Row():
                    mdx23c_input_path = gr.Textbox(
                        label = "Input Path",
                        placeholder = "Place the input path here",
                        interactive = True
                    )
                    mdx23c_output_path = gr.Textbox(
                        label = "Output Path",
                        placeholder = "Place the output path here",
                        interactive = True
                    )
                with gr.Row():
                    mdx23c_bath_button = gr.Button("Separate!", variant = "primary")
                with gr.Row():
                    mdx23c_info = gr.Textbox(
                        label = "Output Information",
                        interactive = False
                    )

            mdx23c_bath_button.click(mdx23c_batch, [mdx23c_input_path, mdx23c_output_path, mdx23c_model, mdx23c_output_format, mdx23c_overlap, mdx23c_segment_size, mdx23c_denoise], [mdx23c_info])

            with gr.Row():
                mdx23c_button = gr.Button("Separate!", variant = "primary")
            with gr.Row():
                mdx23c_stem1 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    label = "Stem 1",
                    type = "filepath"
                )
                mdx23c_stem2 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    label = "Stem 2",
                    type = "filepath"
                )

            mdx23c_button.click(mdxc_separator, [mdx23c_audio, mdx23c_model, mdx23c_output_format, mdx23c_segment_size, mdx23c_overlap, mdx23c_denoise], [mdx23c_stem1, mdx23c_stem2])
        
        with gr.TabItem("MDX-NET"):
            with gr.Row():
                mdxnet_model = gr.Dropdown(
                    label = "Select the Model",
                    choices = mdxnet_models,
                    interactive = True
                )
                mdxnet_output_format = gr.Dropdown(
                    label = "Select the Output Format",
                    choices = output_format,
                    interactive = True
                )
            with gr.Row():
                mdxnet_segment_size = gr.Slider(
                    minimum = 32,
                    maximum = 4000,
                    step = 32,
                    label = "Segment Size",
                    info = "Larger consumes more resources, but may give better results.",
                    value = 256,
                    interactive = True
                )
                mdxnet_overlap = gr.Dropdown(
                        label = "Overlap",
                        choices = mdxnet_overlap_values,
                        value = mdxnet_overlap_values[0],
                        interactive = True
                )
                mdxnet_denoise = gr.Checkbox(
                    label = "Denoise",
                    info = "Enable denoising during separation.",
                    value = True,
                    interactive = True
                )
            with gr.Row():
                mdxnet_audio = gr.Audio(
                    label = "Input Audio",
                    type = "numpy",
                    interactive = True
                )
            with gr.Accordion("Separation by Link", open = False):
                with gr.Row():
                    mdxnet_link = gr.Textbox(
                    label = "Link",
                    placeholder = "Paste the link here",
                    interactive = True
                )
                with gr.Row():
                   gr.Markdown("You can paste the link to the video/audio from many sites, check the complete list [here](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)")
                with gr.Row():
                    mdxnet_download_button = gr.Button(
                    "Download!",
                    variant = "primary"
                )

            mdxnet_download_button.click(download_audio, [mdxnet_link], [mdxnet_audio])

            with gr.Accordion("Batch Separation", open = False):
                with gr.Row():
                    mdxnet_input_path = gr.Textbox(
                        label = "Input Path",
                        placeholder = "Place the input path here",
                        interactive = True
                    )
                    mdxnet_output_path = gr.Textbox(
                        label = "Output Path",
                        placeholder = "Place the output path here",
                        interactive = True
                    )
                with gr.Row():
                    mdxnet_bath_button = gr.Button("Separate!", variant = "primary")
                with gr.Row():
                    mdxnet_info = gr.Textbox(
                        label = "Output Information",
                        interactive = False
                    )

            mdxnet_bath_button.click(mdxnet_batch, [mdxnet_input_path, mdxnet_output_path, mdxnet_model, mdxnet_output_format, mdxnet_overlap, mdxnet_segment_size, mdxnet_denoise], [mdxnet_info])

            with gr.Row():
                mdxnet_button = gr.Button("Separate!", variant = "primary")
            with gr.Row():
                mdxnet_stem1 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    label = "Stem 1",
                    type = "filepath"
                )
                mdxnet_stem2 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    label = "Stem 2",
                    type = "filepath"
                )

            mdxnet_button.click(mdxnet_separator, [mdxnet_audio, mdxnet_model, mdxnet_output_format, mdxnet_segment_size, mdxnet_overlap, mdxnet_denoise], [mdxnet_stem1, mdxnet_stem2])

        with gr.TabItem("VR ARCH"):
            with gr.Row():
                vrarch_model = gr.Dropdown(
                    label = "Select the Model",
                    choices = vrarch_models,
                    interactive = True
                )
                vrarch_output_format = gr.Dropdown(
                    label = "Select the Output Format",
                    choices = output_format,
                    interactive = True
                )
            with gr.Row():
                vrarch_window_size = gr.Dropdown(
                    label = "Window Size",
                    choices = vrarch_window_size_values,
                    value = vrarch_window_size_values[0],
                    interactive = True
                )
                vrarch_agression = gr.Slider(
                    minimum = 1,
                    maximum = 50,
                    step = 1,
                    label = "Agression",
                    info = "Intensity of primary stem extraction.",
                    value = 5,
                    interactive = True
                )
                vrarch_tta = gr.Checkbox(
                    label = "TTA",
                    info = "Enable Test-Time-Augmentation; slow but improves quality.",
                    value = True,
                    visible = True,
                    interactive = True,
                )
                vrarch_high_end_process = gr.Checkbox(
                    label = "High End Process",
                    info = "Mirror the missing frequency range of the output.",
                    value = False,
                    visible = True,
                    interactive = True,
                )
            with gr.Row():
                vrarch_audio = gr.Audio(
                    label = "Input Audio",
                    type = "numpy",
                    interactive = True
                )
            with gr.Accordion("Separation by Link", open = False):
                with gr.Row():
                   vrarch_link = gr.Textbox(
                    label = "Link",
                    placeholder = "Paste the link here",
                    interactive = True
                )
                with gr.Row():
                   gr.Markdown("You can paste the link to the video/audio from many sites, check the complete list [here](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)")
                with gr.Row():
                    vrarch_download_button = gr.Button(
                    "Download!",
                    variant = "primary"
                )

            vrarch_download_button.click(download_audio, [vrarch_link], [vrarch_audio])

            with gr.Accordion("Batch Separation", open = False):
                with gr.Row():
                    vrarch_input_path = gr.Textbox(
                        label = "Input Path",
                        placeholder = "Place the input path here",
                        interactive = True
                    )
                    vrarch_output_path = gr.Textbox(
                        label = "Output Path",
                        placeholder = "Place the output path here",
                        interactive = True
                    )
                with gr.Row():
                    vrarch_bath_button = gr.Button("Separate!", variant = "primary")
                with gr.Row():
                    vrarch_info = gr.Textbox(
                        label = "Output Information",
                        interactive = False
                    )

            vrarch_bath_button.click(vrarch_batch, [vrarch_input_path, vrarch_output_path, vrarch_model, vrarch_output_format, vrarch_window_size, vrarch_agression, vrarch_tta, vrarch_high_end_process], [vrarch_info])

            with gr.Row():
                vrarch_button = gr.Button("Separate!", variant = "primary")
            with gr.Row():
                vrarch_stem1 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    type = "filepath",
                    label = "Stem 1"
                )
                vrarch_stem2 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    type = "filepath",
                    label = "Stem 2"
                )

            vrarch_button.click(vrarch_separator, [vrarch_audio, vrarch_model, vrarch_output_format, vrarch_window_size, vrarch_agression, vrarch_tta, vrarch_high_end_process], [vrarch_stem1, vrarch_stem2])

        with gr.TabItem("Demucs"):
            with gr.Row():
                demucs_model = gr.Dropdown(
                    label = "Select the Model",
                    choices = demucs_models,
                    interactive = True
                )
                demucs_output_format = gr.Dropdown(
                    label = "Select the Output Format",
                    choices = output_format,
                    interactive = True
                )
            with gr.Row():
                demucs_shifts = gr.Slider(
                    minimum = 1,
                    maximum = 20,
                    step = 1,
                    label = "Shifts",
                    info = "Number of predictions with random shifts, higher = slower but better quality.",
                    value = 2,
                    interactive = True
                )
                demucs_overlap = gr.Dropdown(
                   label = "Overlap",
                   choices = demucs_overlap_values,
                   value = demucs_overlap_values[0],
                   interactive = True
                )
            with gr.Row():
                demucs_audio = gr.Audio(
                    label = "Input Audio",
                    type = "numpy",
                    interactive = True
                )
            with gr.Accordion("Separation by Link", open = False):
                with gr.Row():
                    demucs_link = gr.Textbox(
                    label = "Link",
                    placeholder = "Paste the link here",
                    interactive = True
                )
                with gr.Row():
                   gr.Markdown("You can paste the link to the video/audio from many sites, check the complete list [here](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)")
                with gr.Row():
                    demucs_download_button = gr.Button(
                    "Download!",
                    variant = "primary"
                )

            demucs_download_button.click(download_audio, [demucs_link], [demucs_audio])

            with gr.Accordion("Batch Separation", open = False):
                with gr.Row():
                    demucs_input_path = gr.Textbox(
                        label = "Input Path",
                        placeholder = "Place the input path here",
                        interactive = True
                    )
                    demucs_output_path = gr.Textbox(
                        label = "Output Path",
                        placeholder = "Place the output path here",
                        interactive = True
                    )
                with gr.Row():
                    demucs_bath_button = gr.Button("Separate!", variant = "primary")
                with gr.Row():
                    demucs_info = gr.Textbox(
                        label = "Output Information",
                        interactive = False
                    )

            demucs_bath_button.click(demucs_batch, [demucs_input_path, demucs_output_path, demucs_model, demucs_output_format, demucs_shifts, demucs_overlap], [demucs_info])

            with gr.Row():
                demucs_button = gr.Button("Separate!", variant = "primary")
            with gr.Row():
                demucs_stem1 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    type = "filepath",
                    label = "Stem 1"
                )
                demucs_stem2 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    type = "filepath",
                    label = "Stem 2"
                )
            with gr.Row():
                demucs_stem3 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    type = "filepath",
                    label = "Stem 3"
                )
                demucs_stem4 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    type = "filepath",
                    label = "Stem 4"
                )
            
            demucs_button.click(demucs_separator, [demucs_audio, demucs_model, demucs_output_format, demucs_shifts, demucs_overlap], [demucs_stem1, demucs_stem2, demucs_stem3, demucs_stem4])
            
        with gr.TabItem("Themes"):
            select_themes_tab()

        with gr.TabItem("Credits"):
           gr.Markdown(
              """
              UVR5 UI created by **[Eddycrack 864](https://github.com/Eddycrack864).** Join **[AI HUB](https://discord.gg/aihub)** community.
              * python-audio-separator by [beveradb](https://github.com/beveradb).
              * Special thanks to [Ilaria](https://github.com/TheStingerX) for hosting this space and help.
              * Thanks to [Mikus](https://github.com/cappuch) for the help with the code.
              * Thanks to [Nick088](https://huggingface.co/Nick088) for the help to fix roformers.
              * Thanks to [yt_dlp](https://github.com/yt-dlp/yt-dlp) devs.
              * Separation by link source code and improvements by [Blane187](https://huggingface.co/Blane187).
              * Thanks to [ArisDev](https://github.com/aris-py) for porting UVR5 UI to Kaggle and improvements.
              
              
              You can donate to the original UVR5 project here:
              [!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/uvr5)
              """
           )

app.launch(
    share=args.share_enabled,
    server_name="",
    server_port=9999,
)
