import os
import subprocess
import re
import platform
import torch
import logging
import yt_dlp
import gradio as gr
import assets.themes.loadThemes as loadThemes
from audio_separator.separator import Separator
from assets.i18n.i18n import I18nAuto
from argparse import ArgumentParser

i18n = I18nAuto()

device = "cuda" if torch.cuda.is_available() else "cpu"
use_autocast = device == "cuda"

if os.path.isdir("env"):
    if platform.system() == "Windows":
        separator_location = ".\\env\\Scripts\\audio-separator.exe"
    elif platform.system() == "Linux":
        separator_location = "env/bin/audio-separator"
else:
    separator_location = "audio-separator"

if __name__ == "__main__":
    parser = ArgumentParser(
       description="Separate audio into multiple stems",
       epilog="Example: python app.py --share --listen-port 8080 --open"
    )
    parser.add_argument(
       "--share",
       action="store_true",
       help="Enable sharing of the interface through Gradio's temporary URLs"
    )
    parser.add_argument(
       "--listen-port",
       type=int,
       default=9999,
       help="The listening port that the server will use (default: 9999)"
    )
    parser.add_argument(
       "--open",
       action="store_true",
       help="Automatically open the interface in the default web browser"
    )   
    args = parser.parse_args()

#=========================#
#     Roformer Models     #
#=========================#
roformer_models = {
    'BS-Roformer-Viperx-1297': 'model_bs_roformer_ep_317_sdr_12.9755.ckpt',
    'BS-Roformer-Viperx-1296': 'model_bs_roformer_ep_368_sdr_12.9628.ckpt',
    'BS-Roformer-Viperx-1053': 'model_bs_roformer_ep_937_sdr_10.5309.ckpt',
    'Mel-Roformer-Viperx-1143': 'model_mel_band_roformer_ep_3005_sdr_11.4360.ckpt',
    'BS-Roformer-De-Reverb': 'deverb_bs_roformer_8_384dim_10depth.ckpt',
    'Mel-Roformer-Crowd-Aufr33-Viperx': 'mel_band_roformer_crowd_aufr33_viperx_sdr_8.7144.ckpt',
    'Mel-Roformer-Denoise-Aufr33': 'denoise_mel_band_roformer_aufr33_sdr_27.9959.ckpt',
    'Mel-Roformer-Denoise-Aufr33-Aggr' : 'denoise_mel_band_roformer_aufr33_aggr_sdr_27.9768.ckpt',
    'Mel-Roformer-Karaoke-Aufr33-Viperx': 'mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt',
    'MelBand Roformer | Vocals by Kimberley Jensen' : 'vocals_mel_band_roformer.ckpt',
    'MelBand Roformer Kim | FT by unwa' : 'mel_band_roformer_kim_ft_unwa.ckpt',
    'MelBand Roformer Kim | Inst V1 by Unwa' : 'melband_roformer_inst_v1.ckpt',
    'MelBand Roformer Kim | Inst V1 (E) by Unwa' : 'melband_roformer_inst_v1e.ckpt',
    'MelBand Roformer Kim | Inst V2 by Unwa' : 'melband_roformer_inst_v2.ckpt',
    'MelBand Roformer Kim | InstVoc Duality V1 by Unwa' : 'melband_roformer_instvoc_duality_v1.ckpt',
    'MelBand Roformer Kim | InstVoc Duality V2 by Unwa' : 'melband_roformer_instvox_duality_v2.ckpt',
    'MelBand Roformer | De-Reverb by anvuew' : 'dereverb_mel_band_roformer_anvuew_sdr_19.1729.ckpt',
    'MelBand Roformer | De-Reverb Less Aggressive by anvuew' : 'dereverb_mel_band_roformer_less_aggressive_anvuew_sdr_18.8050.ckpt',
    'MelBand Roformer | De-Reverb-Echo by Sucial' : 'dereverb-echo_mel_band_roformer_sdr_10.0169.ckpt',
    'MelBand Roformer | De-Reverb-Echo V2 by Sucial' : 'dereverb-echo_mel_band_roformer_sdr_13.4843_v2.ckpt',
    'MelBand Roformer Kim | SYHFT by SYH99999' : 'MelBandRoformerSYHFT.ckpt',
    'MelBand Roformer Kim | SYHFT V2 by SYH99999' : 'MelBandRoformerSYHFTV2.ckpt',
    'MelBand Roformer Kim | SYHFT V2.5 by SYH99999' : 'MelBandRoformerSYHFTV2.5.ckpt',
    'MelBand Roformer Kim | SYHFT V3 by SYH99999' : 'MelBandRoformerSYHFTV3Epsilon.ckpt',
    'MelBand Roformer Kim | Big SYHFT V1 by SYH99999' : 'MelBandRoformerBigSYHFTV1.ckpt',
    'MelBand Roformer Kim | Big Beta 4 FT by unwa' : 'melband_roformer_big_beta4.ckpt',
    'MelBand Roformer Kim | Big Beta 5e FT by unwa' : 'melband_roformer_big_beta5e.ckpt',
    'BS Roformer | Chorus Male-Female by Sucial' : 'model_chorus_bs_roformer_ep_267_sdr_24.1275.ckpt',
    'MelBand Roformer | Aspiration by Sucial' : 'aspiration_mel_band_roformer_sdr_18.9845.ckpt',
    'MelBand Roformer | Aspiration Less Aggressive by Sucial' : 'aspiration_mel_band_roformer_less_aggr_sdr_18.1201.ckpt',
    'MelBand Roformer | Bleed Suppressor V1 by unwa-97chris' : 'mel_band_roformer_bleed_suppressor_v1.ckpt'
}

#=========================#
#      MDX23C Models      #
#=========================#
mdx23c_models = [
    'MDX23C_D1581.ckpt',
    'MDX23C-8KFFT-InstVoc_HQ.ckpt',
    'MDX23C-8KFFT-InstVoc_HQ_2.ckpt',
    'MDX23C-De-Reverb-aufr33-jarredou.ckpt',
    'MDX23C-DrumSep-aufr33-jarredou.ckpt'
]

#=========================#
#     MDXN-NET Models     #
#=========================#
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
    'UVR-MDX-NET-Inst_HQ_5.onnx',
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

#========================#
#     VR-ARCH Models     #
#========================#
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
    'UVR-De-Reverb-aufr33-jarredou.pth',
    'UVR-DeNoise-Lite.pth',
    'UVR-DeNoise.pth',
    'UVR-BVE-4B_SN-44100-1.pth',
    'MGM_HIGHEND_v4.pth',
    'MGM_LOWEND_A_v4.pth',
    'MGM_LOWEND_B_v4.pth',
    'MGM_MAIN_v4.pth',
]

#=======================#
#     DEMUCS Models     #
#=======================#
demucs_models = [
    'htdemucs_ft.yaml',
    'htdemucs_6s.yaml',
    'htdemucs.yaml',
    'hdemucs_mmi.yaml',
]

output_format = [
    'wav',
    'flac',
    'mp3',
    'ogg',
    'opus',
    'm4a',
    'aiff',
    'ac3'
]

found_files = []
logs = []
out_dir = "./outputs"
models_dir = "./models"
extensions = (".wav", ".flac", ".mp3", ".ogg", ".opus", ".m4a", ".aiff", ".ac3")

def download_audio(url, output_dir="ytdl"):

    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '32',
        }],
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'postprocessor_args': [
            '-acodec', 'pcm_f32le'
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info['title']

            ydl.download([url])

            file_path = os.path.join(output_dir, f"{video_title}.wav")

            if os.path.exists(file_path):
                return os.path.abspath(file_path)
            else:
                raise Exception("Something went wrong")

    except Exception as e:
        raise Exception(f"Error extracting audio with yt-dlp: {str(e)}")

def leaderboard(list_filter):
    try:
        result = subprocess.run(
            [separator_location, "-l", f"--list_filter={list_filter}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        
        return "<table border='1'>" + "".join(
            f"<tr style='{'font-weight: bold; font-size: 1.2em;' if i == 0 else ''}'>" + 
            "".join(f"<td>{cell}</td>" for cell in re.split(r"\s{2,}", line.strip())) + 
            "</tr>" 
            for i, line in enumerate(re.findall(r"^(?!-+)(.+)$", result.stdout.strip(), re.MULTILINE))
        ) + "</table>"
    
    except Exception as e:
        return f"Error: {e}"

def roformer_separator(audio, model_key, out_format, segment_size, override_seg_size, overlap, batch_size, norm_thresh, amp_thresh, single_stem, progress=gr.Progress(track_tqdm=True)):
    base_name = os.path.splitext(os.path.basename(audio))[0]
    roformer_model = roformer_models[model_key]
    try:
        separator = Separator(
            log_level=logging.WARNING,
            model_file_dir=models_dir,
            output_dir=out_dir,
            output_format=out_format,
            use_autocast=use_autocast,
            normalization_threshold=norm_thresh,
            amplification_threshold=amp_thresh,
            output_single_stem=single_stem,
            mdxc_params={
                "segment_size": segment_size,
                "override_model_segment_size": override_seg_size,
                "batch_size": batch_size,
                "overlap": overlap,
            }
        )
    
        progress(0.2, desc="Loading model...")
        separator.load_model(model_filename=roformer_model)

        progress(0.7, desc="Separating audio...")
        separation = separator.separate(audio)

        stems = [os.path.join(out_dir, file_name) for file_name in separation]

        if single_stem.strip():
            return stems[0], None
        
        return stems[0], stems[1]
    
    except Exception as e:
        raise RuntimeError(f"Roformer separation failed: {e}") from e
    
def mdxc_separator(audio, model, out_format, segment_size, override_seg_size, overlap, batch_size, norm_thresh, amp_thresh, single_stem, progress=gr.Progress(track_tqdm=True)):
    base_name = os.path.splitext(os.path.basename(audio))[0]
    try:
        separator = Separator(
            log_level=logging.WARNING,
            model_file_dir=models_dir,
            output_dir=out_dir,
            output_format=out_format,
            use_autocast=use_autocast,
            normalization_threshold=norm_thresh,
            amplification_threshold=amp_thresh,
            output_single_stem=single_stem,
            mdxc_params={
                "segment_size": segment_size,
                "override_model_segment_size": override_seg_size,
                "batch_size": batch_size,
                "overlap": overlap,
            }
        )

        progress(0.2, desc="Loading model...")
        separator.load_model(model_filename=model)

        progress(0.7, desc="Separating audio...")
        separation = separator.separate(audio)

        stems = [os.path.join(out_dir, file_name) for file_name in separation]
        
        if single_stem.strip():
            return stems[0], None
        
        return stems[0], stems[1]

    except Exception as e:
        raise RuntimeError(f"MDX23C separation failed: {e}") from e

def mdxnet_separator(audio, model, out_format, hop_length, segment_size, denoise, overlap, batch_size, norm_thresh, amp_thresh, single_stem, progress=gr.Progress(track_tqdm=True)):
    base_name = os.path.splitext(os.path.basename(audio))[0]
    try:
        separator = Separator(
            log_level=logging.WARNING,
            model_file_dir=models_dir,
            output_dir=out_dir,
            output_format=out_format,
            use_autocast=use_autocast,
            normalization_threshold=norm_thresh,
            amplification_threshold=amp_thresh,
            output_single_stem=single_stem,
            mdx_params={
                "hop_length": hop_length,
                "segment_size": segment_size,
                "overlap": overlap,
                "batch_size": batch_size,
                "enable_denoise": denoise,
            }
        )

        progress(0.2, desc="Loading model...")
        separator.load_model(model_filename=model)

        progress(0.7, desc="Separating audio...")
        separation = separator.separate(audio)

        stems = [os.path.join(out_dir, file_name) for file_name in separation]
        
        if single_stem.strip():
            return stems[0], None
        
        return stems[0], stems[1]

    except Exception as e:
        raise RuntimeError(f"MDX-NET separation failed: {e}") from e

def vrarch_separator(audio, model, out_format, window_size, aggression, tta, post_process, post_process_threshold, high_end_process, batch_size, norm_thresh, amp_thresh, single_stem, progress=gr.Progress(track_tqdm=True)):
    base_name = os.path.splitext(os.path.basename(audio))[0]
    try:
        separator = Separator(
            log_level=logging.WARNING,
            model_file_dir=models_dir,
            output_dir=out_dir,
            output_format=out_format,
            use_autocast=use_autocast,
            normalization_threshold=norm_thresh,
            amplification_threshold=amp_thresh,
            output_single_stem=single_stem,
            vr_params={
                "batch_size": batch_size,
                "window_size": window_size,
                "aggression": aggression,
                "enable_tta": tta,
                "enable_post_process": post_process,
                "post_process_threshold": post_process_threshold,
                "high_end_process": high_end_process,
            }
        )

        progress(0.2, desc="Loading model...")
        separator.load_model(model_filename=model)

        progress(0.7, desc="Separating audio...")
        separation = separator.separate(audio)

        stems = [os.path.join(out_dir, file_name) for file_name in separation]
        
        if single_stem.strip():
            return stems[0], None
        
        return stems[0], stems[1]

    except Exception as e:
        raise RuntimeError(f"VR ARCH separation failed: {e}") from e

def demucs_separator(audio, model, out_format, shifts, segment_size, segments_enabled, overlap, batch_size, norm_thresh, amp_thresh, progress=gr.Progress(track_tqdm=True)):
    base_name = os.path.splitext(os.path.basename(audio))[0]
    try:
        separator = Separator(
            log_level=logging.WARNING,
            model_file_dir=models_dir,
            output_dir=out_dir,
            output_format=out_format,
            use_autocast=use_autocast,
            normalization_threshold=norm_thresh,
            amplification_threshold=amp_thresh,
            demucs_params={
                "batch_size": batch_size,
                "segment_size": segment_size,
                "shifts": shifts,
                "overlap": overlap,
                "segments_enabled": segments_enabled,
            }
        )

        progress(0.2, desc="Loading model...")
        separator.load_model(model_filename=model)

        progress(0.7, desc="Separating audio...")
        separation = separator.separate(audio)

        stems = [os.path.join(out_dir, file_name) for file_name in separation]
        
        if model == "htdemucs_6s.yaml":
            return stems[0], stems[1], stems[2], stems[3], stems[4], stems[5]
        else:
            return stems[0], stems[1], stems[2], stems[3], None, None

    except Exception as e:
        raise RuntimeError(f"Demucs separation failed: {e}") from e

def update_stems(model):
    if model == "htdemucs_6s.yaml":
        return gr.update(visible=True)
    else:
        return gr.update(visible=False)

def roformer_batch(path_input, path_output, model_key, out_format, segment_size, override_seg_size, overlap, batch_size, norm_thresh, amp_thresh, single_stem):
    found_files.clear()
    logs.clear()
    roformer_model = roformer_models[model_key]

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
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            try:
                separator = Separator(
                    log_level=logging.WARNING,
                    model_file_dir=models_dir,
                    output_dir=path_output,
                    output_format=out_format,
                    use_autocast=use_autocast,
                    normalization_threshold=norm_thresh,
                    amplification_threshold=amp_thresh,
                    output_single_stem=single_stem,
                    mdxc_params={
                        "segment_size": segment_size,
                        "override_model_segment_size": override_seg_size,
                        "batch_size": batch_size,
                        "overlap": overlap,
                    }
                )

                logs.append("Loading model...")
                yield "\n".join(logs)
                separator.load_model(model_filename=roformer_model)

                logs.append(f"Separating file: {audio_files}")
                yield "\n".join(logs)
                separator.separate(file_path)
                logs.append(f"File: {audio_files} separated!")
                yield "\n".join(logs)
            except Exception as e:
                raise RuntimeError(f"Roformer batch separation failed: {e}") from e

def mdx23c_batch(path_input, path_output, model, out_format, segment_size, override_seg_size, overlap, batch_size, norm_thresh, amp_thresh, single_stem):
    found_files.clear()
    logs.clear()

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
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            try:
                separator = Separator(
                    log_level=logging.WARNING,
                    model_file_dir=models_dir,
                    output_dir=path_output,
                    output_format=out_format,
                    use_autocast=use_autocast,
                    normalization_threshold=norm_thresh,
                    amplification_threshold=amp_thresh,
                    output_single_stem=single_stem,
                    mdxc_params={
                        "segment_size": segment_size,
                        "override_model_segment_size": override_seg_size,
                        "batch_size": batch_size,
                        "overlap": overlap,
                    }
                )

                logs.append("Loading model...")
                yield "\n".join(logs)
                separator.load_model(model_filename=model)

                logs.append(f"Separating file: {audio_files}")
                yield "\n".join(logs)
                separator.separate(file_path)
                logs.append(f"File: {audio_files} separated!")
                yield "\n".join(logs)
            except Exception as e:
                raise RuntimeError(f"Roformer batch separation failed: {e}") from e

def mdxnet_batch(path_input, path_output, model, out_format, hop_length, segment_size, denoise, overlap, batch_size, norm_thresh, amp_thresh, single_stem):
    found_files.clear()
    logs.clear()

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
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            try:
                separator = Separator(
                    log_level=logging.WARNING,
                    model_file_dir=models_dir,
                    output_dir=path_output,
                    output_format=out_format,
                    use_autocast=use_autocast,
                    normalization_threshold=norm_thresh,
                    amplification_threshold=amp_thresh,
                    output_single_stem=single_stem,
                    mdx_params={
                        "hop_length": hop_length,
                        "segment_size": segment_size,
                        "overlap": overlap,
                        "batch_size": batch_size,
                        "enable_denoise": denoise,
                    }
                )

                logs.append("Loading model...")
                yield "\n".join(logs)
                separator.load_model(model_filename=model)

                logs.append(f"Separating file: {audio_files}")
                yield "\n".join(logs)
                separator.separate(file_path)
                logs.append(f"File: {audio_files} separated!")
                yield "\n".join(logs)
            except Exception as e:
                raise RuntimeError(f"Roformer batch separation failed: {e}") from e

def vrarch_batch(path_input, path_output, model, out_format, window_size, aggression, tta, post_process, post_process_threshold, high_end_process, batch_size, norm_thresh, amp_thresh, single_stem):
    found_files.clear()
    logs.clear()

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
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            try:
                separator = Separator(
                    log_level=logging.WARNING,
                    model_file_dir=models_dir,
                    output_dir=path_output,
                    output_format=out_format,
                    use_autocast=use_autocast,
                    normalization_threshold=norm_thresh,
                    amplification_threshold=amp_thresh,
                    output_single_stem=single_stem,
                    vr_params={
                        "batch_size": batch_size,
                        "window_size": window_size,
                        "aggression": aggression,
                        "enable_tta": tta,
                        "enable_post_process": post_process,
                        "post_process_threshold": post_process_threshold,
                        "high_end_process": high_end_process,
                    }
                )

                logs.append("Loading model...")
                yield "\n".join(logs)
                separator.load_model(model_filename=model)

                logs.append(f"Separating file: {audio_files}")
                yield "\n".join(logs)
                separator.separate(file_path)
                logs.append(f"File: {audio_files} separated!")
                yield "\n".join(logs)
            except Exception as e:
                raise RuntimeError(f"Roformer batch separation failed: {e}") from e

def demucs_batch(path_input, path_output, model, out_format, shifts, segment_size, segments_enabled, overlap, batch_size, norm_thresh, amp_thresh):
    found_files.clear()
    logs.clear()

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
            try:
                separator = Separator(
                    log_level=logging.WARNING,
                    model_file_dir=models_dir,
                    output_dir=path_output,
                    output_format=out_format,
                    use_autocast=use_autocast,
                    normalization_threshold=norm_thresh,
                    amplification_threshold=amp_thresh,
                    demucs_params={
                        "batch_size": batch_size,
                        "segment_size": segment_size,
                        "shifts": shifts,
                        "overlap": overlap,
                        "segments_enabled": segments_enabled,
                    }
                )

                logs.append("Loading model...")
                yield "\n".join(logs)
                separator.load_model(model_filename=model)

                logs.append(f"Separating file: {audio_files}")
                yield "\n".join(logs)
                separator.separate(file_path)
                logs.append(f"File: {audio_files} separated!")
                yield "\n".join(logs)
            except Exception as e:
                raise RuntimeError(f"Roformer batch separation failed: {e}") from e
            
with gr.Blocks(theme = loadThemes.load_json() or "NoCrypt/miku", title = "🎵 UVR5 UI 🎵") as app:
    gr.Markdown("<h1> 🎵 UVR5 UI 🎵 </h1>")
    gr.Markdown(i18n("If you like UVR5 UI you can star my repo on [GitHub](https://github.com/Eddycrack864/UVR5-UI)"))
    gr.Markdown(i18n("Try UVR5 UI on Hugging Face with A100 [here](https://huggingface.co/spaces/TheStinger/UVR5_UI)"))
    with gr.Tabs():
        with gr.TabItem("BS/Mel Roformer"):
            with gr.Row():
                roformer_model = gr.Dropdown(
                    label = i18n("Select the model"),
                    choices = list(roformer_models.keys()),
                    value = lambda : None,
                    interactive = True
                )
                roformer_output_format = gr.Dropdown(
                    label = i18n("Select the output format"),
                    choices = output_format,
                    value = lambda : None,
                    interactive = True
                )
            with gr.Accordion(i18n("Advanced settings"), open = False):
                with gr.Group():
                    with gr.Row():
                        roformer_segment_size = gr.Slider(
                            label = i18n("Segment size"),
                            info = i18n("Larger consumes more resources, but may give better results"),
                            minimum = 32,
                            maximum = 4000,
                            step = 32,
                            value = 256,
                            interactive = True
                        )
                        roformer_override_segment_size = gr.Checkbox(
                            label = i18n("Override segment size"),
                            info = i18n("Override model default segment size instead of using the model default value"),
                            value = False,
                            interactive = True
                        )
                    with gr.Row():
                        roformer_overlap = gr.Slider(
                            label = i18n("Overlap"),
                            info = i18n("Amount of overlap between prediction windows"),
                            minimum = 2,
                            maximum = 10,
                            step = 1,
                            value = 8,
                            interactive = True
                        )
                        roformer_batch_size = gr.Slider(
                            label = i18n("Batch size"),
                            info = i18n("Larger consumes more RAM but may process slightly faster"),
                            minimum = 1,
                            maximum = 16,
                            step = 1,
                            value = 1,
                            interactive = True
                        )
                    with gr.Row():
                        roformer_normalization_threshold = gr.Slider(
                            label = i18n("Normalization threshold"),
                            info = i18n("The threshold for audio normalization"),
                            minimum = 0.1,
                            maximum = 1,
                            step = 0.1,
                            value = 0.9,
                            interactive = True
                        )
                        roformer_amplification_threshold = gr.Slider(
                            label = i18n("Amplification threshold"),
                            info = i18n("The threshold for audio amplification"),
                            minimum = 0.1,
                            maximum = 1,
                            step = 0.1,
                            value = 0.7,
                            interactive = True
                        )
                    with gr.Row():
                        roformer_single_stem = gr.Textbox(
                            label = i18n("Output only single stem"),
                            placeholder = i18n("Write the stem you want, check the stems of each model on Leaderboard. e.g. Instrumental"),
                            interactive = True
                        )
            with gr.Row():
                roformer_audio = gr.Audio(
                    label = i18n("Input audio"),
                    type = "filepath",
                    interactive = True
                )
            with gr.Accordion(i18n("Separation by link"), open = False):
                with gr.Row():
                    roformer_link = gr.Textbox(
                        label = i18n("Link"),
                        placeholder = i18n("Paste the link here"),
                        interactive = True
                    )
                with gr.Row():
                    gr.Markdown(i18n("You can paste the link to the video/audio from many sites, check the complete list [here](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)"))
                with gr.Row():
                    roformer_download_button = gr.Button(
                        i18n("Download!"),
                        variant = "primary"
                    )

            roformer_download_button.click(download_audio, [roformer_link], [roformer_audio])

            with gr.Accordion(i18n("Batch separation"), open = False):
                with gr.Row():
                    roformer_input_path = gr.Textbox(
                        label = i18n("Input path"),
                        placeholder = i18n("Place the input path here"),
                        interactive = True
                    )
                    roformer_output_path = gr.Textbox(
                        label = i18n("Output path"),
                        placeholder = i18n("Place the output path here"),
                        interactive = True
                    )
                with gr.Row():
                    roformer_bath_button = gr.Button(i18n("Separate!"), variant = "primary")
                with gr.Row():
                    roformer_info = gr.Textbox(
                        label = i18n("Output information"),
                        interactive = False
                    )

            roformer_bath_button.click(roformer_batch, [roformer_input_path, roformer_output_path, roformer_model, roformer_output_format, roformer_segment_size, roformer_override_segment_size, roformer_overlap, roformer_batch_size, roformer_normalization_threshold, roformer_amplification_threshold, roformer_single_stem], [roformer_info])

            with gr.Row():
                roformer_button = gr.Button(i18n("Separate!"), variant = "primary")
            with gr.Row():
                roformer_stem1 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    label = i18n("Stem 1"),
                    type = "filepath"
                )
                roformer_stem2 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    label = i18n("Stem 2"),
                    type = "filepath"
                )

            roformer_button.click(roformer_separator, [roformer_audio, roformer_model, roformer_output_format, roformer_segment_size, roformer_override_segment_size, roformer_overlap, roformer_batch_size, roformer_normalization_threshold, roformer_amplification_threshold, roformer_single_stem], [roformer_stem1, roformer_stem2])

        with gr.TabItem("MDX23C"):
            with gr.Row():
                mdx23c_model = gr.Dropdown(
                    label = i18n("Select the model"),
                    choices = mdx23c_models,
                    value = lambda : None,
                    interactive = True
                )
                mdx23c_output_format = gr.Dropdown(
                    label = i18n("Select the output format"),
                    choices = output_format,
                    value = lambda : None,
                    interactive = True
                )
            with gr.Accordion(i18n("Advanced settings"), open = False):
                with gr.Group():
                    with gr.Row():
                        mdx23c_segment_size = gr.Slider(
                            minimum = 32,
                            maximum = 4000,
                            step = 32,
                            label = i18n("Segment size"),
                            info = i18n("Larger consumes more resources, but may give better results"),
                            value = 256,
                            interactive = True
                        )
                        mdx23c_override_segment_size = gr.Checkbox(
                            label = i18n("Override segment size"),
                            info = i18n("Override model default segment size instead of using the model default value"),
                            value = False,
                            interactive = True
                        )
                    with gr.Row():
                        mdx23c_overlap = gr.Slider(
                            minimum = 2,
                            maximum = 50,
                            step = 1,
                            label = i18n("Overlap"),
                            info = i18n("Amount of overlap between prediction windows"),
                            value = 8,
                            interactive = True
                        )
                        mdx23c_batch_size = gr.Slider(
                            label = i18n("Batch size"),
                            info = i18n("Larger consumes more RAM but may process slightly faster"),
                            minimum = 1,
                            maximum = 16,
                            step = 1,
                            value = 1,
                            interactive = True
                        )
                    with gr.Row():
                        mdx23c_normalization_threshold = gr.Slider(
                            label = i18n("Normalization threshold"),
                            info = i18n("The threshold for audio normalization"),
                            minimum = 0.1,
                            maximum = 1,
                            step = 0.1,
                            value = 0.9,
                            interactive = True
                        )
                        mdx23c_amplification_threshold = gr.Slider(
                            label = i18n("Amplification threshold"),
                            info = i18n("The threshold for audio amplification"),
                            minimum = 0.1,
                            maximum = 1,
                            step = 0.1,
                            value = 0.7,
                            interactive = True
                        )
                    with gr.Row():
                        mdx23c_single_stem = gr.Textbox(
                            label = i18n("Output only single stem"),
                            placeholder = i18n("Write the stem you want, check the stems of each model on Leaderboard. e.g. Instrumental"),
                            interactive = True
                        )
            with gr.Row():
                mdx23c_audio = gr.Audio(
                    label = i18n("Input audio"),
                    type = "filepath",
                    interactive = True
                )
            with gr.Accordion(i18n("Separation by link"), open = False):
                with gr.Row():
                    mdx23c_link = gr.Textbox(
                        label = i18n("Link"),
                        placeholder = i18n("Paste the link here"),
                        interactive = True
                    )
                with gr.Row():
                    gr.Markdown(i18n("You can paste the link to the video/audio from many sites, check the complete list [here](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)"))
                with gr.Row():
                    mdx23c_download_button = gr.Button(
                        i18n("Download!"),
                        variant = "primary"
                    )

            mdx23c_download_button.click(download_audio, [mdx23c_link], [mdx23c_audio])

            with gr.Accordion(i18n("Batch separation"), open = False):
                with gr.Row():
                    mdx23c_input_path = gr.Textbox(
                        label = i18n("Input path"),
                        placeholder = i18n("Place the input path here"),
                        interactive = True
                    )
                    mdx23c_output_path = gr.Textbox(
                        label = i18n("Output path"),
                        placeholder = i18n("Place the output path here"),
                        interactive = True
                    )
                with gr.Row():
                    mdx23c_bath_button = gr.Button(i18n("Separate!"), variant = "primary")
                with gr.Row():
                    mdx23c_info = gr.Textbox(
                        label = i18n("Output information"),
                        interactive = False
                    )

            mdx23c_bath_button.click(mdx23c_batch, [mdx23c_input_path, mdx23c_output_path, mdx23c_model, mdx23c_output_format, mdx23c_segment_size, mdx23c_override_segment_size, mdx23c_overlap, mdx23c_batch_size, mdx23c_normalization_threshold, mdx23c_amplification_threshold, mdx23c_single_stem], [mdx23c_info])

            with gr.Row():
                mdx23c_button = gr.Button(i18n("Separate!"), variant = "primary")
            with gr.Row():
                mdx23c_stem1 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    label = i18n("Stem 1"),
                    type = "filepath"
                )
                mdx23c_stem2 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    label = i18n("Stem 2"),
                    type = "filepath"
                )

            mdx23c_button.click(mdxc_separator, [mdx23c_audio, mdx23c_model, mdx23c_output_format, mdx23c_segment_size, mdx23c_override_segment_size, mdx23c_overlap, mdx23c_batch_size, mdx23c_normalization_threshold, mdx23c_amplification_threshold, mdx23c_single_stem], [mdx23c_stem1, mdx23c_stem2])
                
        with gr.TabItem("MDX-NET"):
            with gr.Row():
                mdxnet_model = gr.Dropdown(
                    label = i18n("Select the model"),
                    choices = mdxnet_models,
                    value = lambda : None,
                    interactive = True
                )
                mdxnet_output_format = gr.Dropdown(
                    label = i18n("Select the output format"),
                    choices = output_format,
                    value = lambda : None,
                    interactive = True
                )
            with gr.Accordion(i18n("Advanced settings"), open = False):
                with gr.Group():
                    with gr.Row():
                        mdxnet_hop_length = gr.Slider(
                            label = i18n("Hop length"),
                            info = i18n("Usually called stride in neural networks; only change if you know what you're doing"),
                            minimum = 32,
                            maximum = 2048,
                            step = 32,
                            value = 1024,
                            interactive = True
                        )
                        mdxnet_segment_size = gr.Slider(
                            minimum = 32,
                            maximum = 4000,
                            step = 32,
                            label = i18n("Segment size"),
                            info = i18n("Larger consumes more resources, but may give better results"),
                            value = 256,
                            interactive = True
                        )
                        mdxnet_denoise = gr.Checkbox(
                            label = i18n("Denoise"),
                            info = i18n("Enable denoising during separation"),
                            value = True,
                            interactive = True
                        )
                    with gr.Row():
                        mdxnet_overlap = gr.Slider(
                            label = i18n("Overlap"),
                            info = i18n("Amount of overlap between prediction windows"),
                            minimum = 0.001,
                            maximum = 0.999,
                            step = 0.001,
                            value = 0.25,
                            interactive = True
                        )
                        mdxnet_batch_size = gr.Slider(
                            label = i18n("Batch size"),
                            info = i18n("Larger consumes more RAM but may process slightly faster"),
                            minimum = 1,
                            maximum = 16,
                            step = 1,
                            value = 1,
                            interactive = True
                        )
                    with gr.Row():
                        mdxnet_normalization_threshold = gr.Slider(
                            label = i18n("Normalization threshold"),
                            info = i18n("The threshold for audio normalization"),
                            minimum = 0.1,
                            maximum = 1,
                            step = 0.1,
                            value = 0.9,
                            interactive = True
                        )
                        mdxnet_amplification_threshold = gr.Slider(
                            label = i18n("Amplification threshold"),
                            info = i18n("The threshold for audio amplification"),
                            minimum = 0.1,
                            maximum = 1,
                            step = 0.1,
                            value = 0.7,
                            interactive = True
                        )
                    with gr.Row():
                        mdxnet_single_stem = gr.Textbox(
                            label = i18n("Output only single stem"),
                            placeholder = i18n("Write the stem you want, check the stems of each model on Leaderboard. e.g. Instrumental"),
                            interactive = True
                        )
            with gr.Row():
                mdxnet_audio = gr.Audio(
                    label = i18n("Input audio"),
                    type = "filepath",
                    interactive = True
                )
            with gr.Accordion(i18n("Separation by link"), open = False):
                with gr.Row():
                    mdxnet_link = gr.Textbox(
                        label = i18n("Link"),
                        placeholder = i18n("Paste the link here"),
                        interactive = True
                    )
                with gr.Row():
                    gr.Markdown(i18n("You can paste the link to the video/audio from many sites, check the complete list [here](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)"))
                with gr.Row():
                    mdxnet_download_button = gr.Button(
                        i18n("Download!"),
                        variant = "primary"
                    )
                
            mdxnet_download_button.click(download_audio, [mdxnet_link], [mdxnet_audio])

            with gr.Accordion(i18n("Batch separation"), open = False):
                with gr.Row():
                    mdxnet_input_path = gr.Textbox(
                        label = i18n("Input path"),
                        placeholder = i18n("Place the input path here"),
                        interactive = True
                    )
                    mdxnet_output_path = gr.Textbox(
                        label = i18n("Output path"),
                        placeholder = i18n("Place the output path here"),
                        interactive = True
                    )
                with gr.Row():
                    mdxnet_bath_button = gr.Button(i18n("Separate!"), variant = "primary")
                with gr.Row():
                    mdxnet_info = gr.Textbox(
                        label = i18n("Output information"),
                        interactive = False
                    )

            mdxnet_bath_button.click(mdxnet_batch, [mdxnet_input_path, mdxnet_output_path, mdxnet_model, mdxnet_output_format, mdxnet_hop_length, mdxnet_segment_size, mdxnet_denoise, mdxnet_overlap, mdxnet_batch_size, mdxnet_normalization_threshold, mdxnet_amplification_threshold, mdxnet_single_stem], [mdxnet_info])

            with gr.Row():
                mdxnet_button = gr.Button(i18n("Separate!"), variant = "primary")
            with gr.Row():
                mdxnet_stem1 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    label = i18n("Stem 1"),
                    type = "filepath"
                )
                mdxnet_stem2 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    label = i18n("Stem 2"),
                    type = "filepath"
                )

            mdxnet_button.click(mdxnet_separator, [mdxnet_audio, mdxnet_model, mdxnet_output_format, mdxnet_hop_length, mdxnet_segment_size, mdxnet_denoise, mdxnet_overlap, mdxnet_batch_size, mdxnet_normalization_threshold, mdxnet_amplification_threshold, mdxnet_single_stem], [mdxnet_stem1, mdxnet_stem2])

        with gr.TabItem("VR ARCH"):
            with gr.Row():
                vrarch_model = gr.Dropdown(
                    label = i18n("Select the model"),
                    choices = vrarch_models,
                    value = lambda : None,
                    interactive = True
                )
                vrarch_output_format = gr.Dropdown(
                    label = i18n("Select the output format"),
                    choices = output_format,
                    value = lambda : None,
                    interactive = True
                )
            with gr.Accordion(i18n("Advanced settings"), open = False):
                with gr.Group():
                    with gr.Row():
                        vrarch_window_size = gr.Slider(
                            label = i18n("Window size"),
                            info = i18n("Balance quality and speed. 1024 = fast but lower, 320 = slower but better quality"),
                            minimum=320,
                            maximum=1024,
                            step=32,
                            value = 512,
                            interactive = True
                        )
                        vrarch_agression = gr.Slider(
                            minimum = 1,
                            maximum = 50,
                            step = 1,
                            label = i18n("Agression"),
                            info = i18n("Intensity of primary stem extraction"),
                            value = 5,
                            interactive = True
                        )
                        vrarch_tta = gr.Checkbox(
                            label = i18n("TTA"),
                            info = i18n("Enable Test-Time-Augmentation; slow but improves quality"),
                            value = True,
                            visible = True,
                            interactive = True
                        )
                    with gr.Row():
                        vrarch_post_process = gr.Checkbox(
                            label = i18n("Post process"),
                            info = i18n("Identify leftover artifacts within vocal output; may improve separation for some songs"),
                            value = False,
                            visible = True,
                            interactive = True
                        )
                        vrarch_post_process_threshold = gr.Slider(
                            label = i18n("Post process threshold"),
                            info = i18n("Threshold for post-processing"),
                            minimum = 0.1,
                            maximum = 0.3,
                            step = 0.1,
                            value = 0.2,
                            interactive = True
                        )
                    with gr.Row():
                        vrarch_high_end_process = gr.Checkbox(
                            label = i18n("High end process"),
                            info = i18n("Mirror the missing frequency range of the output"),
                            value = False,
                            visible = True,
                            interactive = True,
                        )
                        vrarch_batch_size = gr.Slider(
                            label = i18n("Batch size"),
                            info = i18n("Larger consumes more RAM but may process slightly faster"),
                            minimum = 1,
                            maximum = 16,
                            step = 1,
                            value = 1,
                            interactive = True
                        )
                    with gr.Row():
                        vrarch_normalization_threshold = gr.Slider(
                            label = i18n("Normalization threshold"),
                            info = i18n("The threshold for audio normalization"),
                            minimum = 0.1,
                            maximum = 1,
                            step = 0.1,
                            value = 0.9,
                            interactive = True
                        )
                        vrarch_amplification_threshold = gr.Slider(
                            label = i18n("Amplification threshold"),
                            info = i18n("The threshold for audio amplification"),
                            minimum = 0.1,
                            maximum = 1,
                            step = 0.1,
                            value = 0.7,
                            interactive = True
                        )
                    with gr.Row():
                        vrarch_single_stem = gr.Textbox(
                            label = i18n("Output only single stem"),
                            placeholder = i18n("Write the stem you want, check the stems of each model on Leaderboard. e.g. Instrumental"),
                            interactive = True
                        )
            with gr.Row():
                vrarch_audio = gr.Audio(
                    label = i18n("Input audio"),
                    type = "filepath",
                    interactive = True
                )
            with gr.Accordion(i18n("Separation by link"), open = False):
                with gr.Row():
                    vrarch_link = gr.Textbox(
                        label = i18n("Link"),
                        placeholder = i18n("Paste the link here"),
                        interactive = True
                    )
                with gr.Row():
                    gr.Markdown(i18n("You can paste the link to the video/audio from many sites, check the complete list [here](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)"))
                with gr.Row():
                    vrarch_download_button = gr.Button(
                        i18n("Download!"),
                        variant = "primary"
                )

            vrarch_download_button.click(download_audio, [vrarch_link], [vrarch_audio])
            
            with gr.Accordion(i18n("Batch separation"), open = False):
                with gr.Row():
                    vrarch_input_path = gr.Textbox(
                        label = i18n("Input path"),
                        placeholder = i18n("Place the input path here"),
                        interactive = True
                    )
                    vrarch_output_path = gr.Textbox(
                        label = i18n("Output path"),
                        placeholder = i18n("Place the output path here"),
                        interactive = True
                    )
                with gr.Row():
                    vrarch_bath_button = gr.Button(i18n("Separate!"), variant = "primary")
                with gr.Row():
                    vrarch_info = gr.Textbox(
                        label = i18n("Output information"),
                        interactive = False
                    )

            vrarch_bath_button.click(vrarch_batch, [vrarch_input_path, vrarch_output_path, vrarch_model, vrarch_output_format, vrarch_window_size, vrarch_agression, vrarch_tta, vrarch_post_process, vrarch_post_process_threshold, vrarch_high_end_process, vrarch_batch_size, vrarch_normalization_threshold, vrarch_amplification_threshold, vrarch_single_stem], [vrarch_info])

            with gr.Row():
                vrarch_button = gr.Button(i18n("Separate!"), variant = "primary")
            with gr.Row():
                vrarch_stem1 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    type = "filepath",
                    label = i18n("Stem 1")
                )
                vrarch_stem2 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    type = "filepath",
                    label = i18n("Stem 2")
                )

            vrarch_button.click(vrarch_separator, [vrarch_audio, vrarch_model, vrarch_output_format, vrarch_window_size, vrarch_agression, vrarch_tta, vrarch_post_process, vrarch_post_process_threshold, vrarch_high_end_process, vrarch_batch_size, vrarch_normalization_threshold, vrarch_amplification_threshold, vrarch_single_stem], [vrarch_stem1, vrarch_stem2])

        with gr.TabItem("Demucs"):
            with gr.Row():
                demucs_model = gr.Dropdown(
                    label = i18n("Select the model"),
                    choices = demucs_models,
                    value = lambda : None,
                    interactive = True
                )
                demucs_output_format = gr.Dropdown(
                    label = i18n("Select the output format"),
                    choices = output_format,
                    value = lambda : None,
                    interactive = True
                )
            with gr.Accordion(i18n("Advanced settings"), open = False):
                with gr.Group():
                    with gr.Row():
                        demucs_shifts = gr.Slider(
                            label = i18n("Shifts"),
                            info = i18n("Number of predictions with random shifts, higher = slower but better quality"),
                            minimum = 1,
                            maximum = 20,
                            step = 1,
                            value = 2,
                            interactive = True
                        )
                        demucs_segment_size = gr.Slider(
                            label = i18n("Segment size"),
                            info = i18n("Size of segments into which the audio is split. Higher = slower but better quality"),
                            minimum = 1,
                            maximum = 100,
                            step = 1,
                            value = 40,
                            interactive = True
                        )
                        demucs_segments_enabled = gr.Checkbox(
                            label = i18n("Segment-wise processing"),
                            info = i18n("Enable segment-wise processing"),
                            value = True,
                            interactive = True
                        )
                    with gr.Row():
                        demucs_overlap = gr.Slider(
                            label = i18n("Overlap"),
                            info = i18n("Overlap between prediction windows. Higher = slower but better quality"),
                            minimum=0.001,
                            maximum=0.999,
                            step=0.001,
                            value = 0.25,
                            interactive = True
                        )
                        demucs_batch_size = gr.Slider(
                            label = i18n("Batch size"),
                            info = i18n("Larger consumes more RAM but may process slightly faster"),
                            minimum = 1,
                            maximum = 16,
                            step = 1,
                            value = 1,
                            interactive = True
                        )
                    with gr.Row():
                        demucs_normalization_threshold = gr.Slider(
                            label = i18n("Normalization threshold"),
                            info = i18n("The threshold for audio normalization"),
                            minimum = 0.1,
                            maximum = 1,
                            step = 0.1,
                            value = 0.9,
                            interactive = True
                        )
                        demucs_amplification_threshold = gr.Slider(
                            label = i18n("Amplification threshold"),
                            info = i18n("The threshold for audio amplification"),
                            minimum = 0.1,
                            maximum = 1,
                            step = 0.1,
                            value = 0.7,
                            interactive = True
                        )
            with gr.Row():
                demucs_audio = gr.Audio(
                    label = i18n("Input audio"),
                    type = "filepath",
                    interactive = True
                )
            with gr.Accordion(i18n("Separation by link"), open = False):
                with gr.Row():
                    demucs_link = gr.Textbox(
                        label = i18n("Link"),
                        placeholder = i18n("Paste the link here"),
                        interactive = True
                    )
                with gr.Row():
                    gr.Markdown(i18n("You can paste the link to the video/audio from many sites, check the complete list [here](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)"))
                with gr.Row():
                    demucs_download_button = gr.Button(
                        i18n("Download!"),
                        variant = "primary"
                    )

            demucs_download_button.click(download_audio, [demucs_link], [demucs_audio])

            with gr.Accordion(i18n("Batch separation"), open = False):
                with gr.Row():
                    demucs_input_path = gr.Textbox(
                        label = i18n("Input path"),
                        placeholder = i18n("Place the input path here"),
                        interactive = True
                    )
                    demucs_output_path = gr.Textbox(
                        label = i18n("Output path"),
                        placeholder = i18n("Place the output path here"),
                        interactive = True
                    )
                with gr.Row():
                    demucs_bath_button = gr.Button(i18n("Separate!"), variant = "primary")
                with gr.Row():
                    demucs_info = gr.Textbox(
                        label = i18n("Output information"),
                        interactive = False
                    )

            demucs_bath_button.click(demucs_batch, [demucs_input_path, demucs_output_path, demucs_model, demucs_output_format, demucs_shifts, demucs_segment_size, demucs_segments_enabled, demucs_overlap, demucs_batch_size, demucs_normalization_threshold, demucs_amplification_threshold], [demucs_info])

            with gr.Row():
                demucs_button = gr.Button(i18n("Separate!"), variant = "primary")
            with gr.Row():
                demucs_stem1 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    type = "filepath",
                    label = i18n("Stem 1")
                )
                demucs_stem2 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    type = "filepath",
                    label = i18n("Stem 2")
                )
            with gr.Row():
                demucs_stem3 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    type = "filepath",
                    label = i18n("Stem 3")
                )
                demucs_stem4 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    type = "filepath",
                    label = i18n("Stem 4")
                )
            with gr.Row(visible=False) as stem6:
                demucs_stem5 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    type = "filepath",
                    label = i18n("Stem 5")
                )
                demucs_stem6 = gr.Audio(
                    show_download_button = True,
                    interactive = False,
                    type = "filepath",
                    label = i18n("Stem 6")
                )

            demucs_model.change(update_stems, inputs=[demucs_model], outputs=stem6)
                
            demucs_button.click(demucs_separator, [demucs_audio, demucs_model, demucs_output_format, demucs_shifts, demucs_segment_size, demucs_segments_enabled, demucs_overlap, demucs_batch_size, demucs_normalization_threshold, demucs_amplification_threshold], [demucs_stem1, demucs_stem2, demucs_stem3, demucs_stem4, demucs_stem5, demucs_stem6])

        with gr.TabItem(i18n("Leaderboard")):
            with gr.Group():
                with gr.Row(equal_height=True):
                    list_filter = gr.Dropdown(
                        label = i18n("List filter"),
                        info = i18n("Filter and sort the model list by stem"),
                        choices = ["vocals", "instrumental", "reverb", "echo", "noise", "crowd", "dry", "aspiration", "male", "woodwinds", "kick", "drums", "bass", "guitar", "piano", "other"],
                        value = lambda : None
                    )
                    list_button = gr.Button(i18n("Show list!"), variant = "primary")
            output_list = gr.HTML(label = i18n("Leaderboard"))

            list_button.click(leaderboard, inputs=list_filter, outputs=output_list)

        with gr.TabItem(i18n("Themes")):
            themes_select = gr.Dropdown(
                label = i18n("Theme"),
                info = i18n("Select the theme you want to use. (Requires restarting the App)"),
                choices = loadThemes.get_list(),
                value = loadThemes.read_json(),
                visible = True
            )
            dummy_output = gr.Textbox(visible = False)

            themes_select.change(
                fn = loadThemes.select_theme,
                inputs = themes_select,
                outputs = [dummy_output]
            )

        with gr.TabItem(i18n("Credits")):
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
                * Thanks to [Bebra777228](https://github.com/Bebra777228)'s code for guiding me to improve my code.
                * Thanks to Nick088, MrM0dZ, Ryouko-Yamanda65777, lucinamari, perariroswe and Enes for helping translate UVR5 UI.
                
                You can donate to the original UVR5 project here:
                [!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/uvr5)
                """
            )

app.launch(
    share=args.share,
    server_name="",
    server_port=args.listen_port,
    inbrowser=args.open
)