import asyncio
import os
from pathlib import Path

from admin.services.mvsep_service import MVSepService


async def run_single_mvsep_job(input_path: str, output_dir: str, skip_stage_1: bool = False) -> None:
    api_key = os.getenv("MVSEP_API_KEY")
    if not api_key:
        raise RuntimeError("MVSEP_API_KEY environment variable is not set.")

    input_path = str(Path(input_path).resolve())
    output_dir = str(Path(output_dir).resolve())

    print(f"Input file: {input_path}")
    print(f"Output dir: {output_dir}")
    print(f"skip_stage_1: {skip_stage_1}")

    os.makedirs(output_dir, exist_ok=True)

    def progress_cb(p: float, msg: str) -> None:
        pct = int(round(p * 100))
        print(f"[{pct:3d}%] {msg}")

    service = MVSepService(api_key=api_key)

    result_files = await service.process_audio_file(
        input_file=input_path,
        output_dir=output_dir,
        progress_callback=progress_cb,
        skip_stage_1=skip_stage_1,
        keep_original_mix=True,
        keep_drum_stem=True,
    )

    print("\n=== MVSep result files ===")
    for name, path in result_files.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    # EXAMPLE: run on one of your DrumBeats originals.
    # You can change this to any clip you want.
    input_clip = r"F:\DrumTracKAI_v1.1.17\DrumBeats\rosanna_original.wav"

    # Where to store stems for this test run
    output_dir = r"F:\DrumTracKAI_v1.1.17\admin\data\mvsep_test_rosanna"

    # For original mix, we want full 2-stage (HDemucs + DrumSep), so skip_stage_1=False
    asyncio.run(run_single_mvsep_job(input_clip, output_dir, skip_stage_1=False))
