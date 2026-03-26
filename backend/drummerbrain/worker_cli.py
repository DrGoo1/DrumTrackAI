import argparse
import json
import os
from pathlib import Path

from . import db as dtkdb

from .ingest_drumbeats import main as ingest_drumbeats_main
from .ingest_audio_phrases import main as ingest_audio_phrases_main
from .ingest_transcription_artifacts import main as ingest_transcription_artifacts_main
from .ingest_written_references import main as ingest_written_references_main
from .eval_harness import main as eval_harness_main
from admin.services.dataset_roots import resolve_dataset_roots


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_ing = sub.add_parser("ingest-drumbeats")
    p_ing.add_argument("--root")
    p_ing.add_argument("--limit", type=int)

    p_phr = sub.add_parser("ingest-audio-phrases")
    p_phr.add_argument("--root", required=True)
    p_phr.add_argument("--dataset-id", required=True)
    p_phr.add_argument("--label", required=True)
    p_phr.add_argument("--limit", type=int)

    p_stl = sub.add_parser("ingest-soundtracksloops")
    p_stl.add_argument("--root")
    p_stl.add_argument("--limit", type=int)

    p_snr = sub.add_parser("ingest-snare-rudiments")
    p_snr.add_argument("--root")
    p_snr.add_argument("--limit", type=int)

    p_ta = sub.add_parser("ingest-transcription-artifacts")
    p_ta.add_argument("--db-path")
    p_ta.add_argument("--in", dest="in_path", required=True)
    p_ta.add_argument("--transcription-version", required=True)
    p_ta.add_argument("--skip-missing-assets", action="store_true")

    p_wr = sub.add_parser("ingest-written-references")
    p_wr.add_argument("--db-path")
    p_wr.add_argument("--in", dest="in_path", required=True)
    p_wr.add_argument("--dataset-id", required=True)
    p_wr.add_argument("--label", required=True)
    p_wr.add_argument("--dataset-type", default="written_reference")
    p_wr.add_argument("--transcription-version", required=True)
    p_wr.add_argument("--root-path", default="")
    p_wr.add_argument("--default-meter", default="4/4")
    p_wr.add_argument("--default-resolution-ppq", type=int, default=480)
    p_wr.add_argument("--default-subdiv", type=int, default=4)

    p_ds = sub.add_parser("datasets")
    p_ds_sub = p_ds.add_subparsers(dest="datasets_cmd", required=True)

    p_ds_list = p_ds_sub.add_parser("list")
    p_ds_list.add_argument("--db-path")

    p_ds_enable = p_ds_sub.add_parser("enable")
    p_ds_enable.add_argument("dataset_id")
    p_ds_enable.add_argument("--db-path")

    p_ds_disable = p_ds_sub.add_parser("disable")
    p_ds_disable.add_argument("dataset_id")
    p_ds_disable.add_argument("--db-path")

    p_fw = sub.add_parser("flywheel-run")
    p_fw.add_argument("--db-path")
    p_fw.add_argument("--out", required=True)
    p_fw.add_argument("--baseline")
    p_fw.add_argument("--fail-on-checks", action="store_true")
    p_fw.add_argument("--cases-path")

    p_fw.add_argument("--ingest-drumbeats", action="store_true")
    p_fw.add_argument("--ingest-audio-phrases-root")
    p_fw.add_argument("--ingest-audio-phrases-dataset-id")
    p_fw.add_argument("--ingest-audio-phrases-label")
    p_fw.add_argument("--ingest-audio-phrases-limit", type=int)

    p_fw.add_argument("--ingest-written-refs-in")
    p_fw.add_argument("--ingest-written-refs-dataset-id")
    p_fw.add_argument("--ingest-written-refs-label")
    p_fw.add_argument("--ingest-written-refs-transcription-version")

    p_fw.add_argument("--import-artifacts-in")
    p_fw.add_argument("--import-artifacts-transcription-version")
    p_fw.add_argument("--import-artifacts-skip-missing-assets", action="store_true")

    p_eval = sub.add_parser("eval")
    p_eval.add_argument("--db-path")
    p_eval.add_argument("--cases-path")
    p_eval.add_argument("--out", required=True)
    p_eval.add_argument("--limit-cases", type=int)
    p_eval.add_argument("--baseline")
    p_eval.add_argument("--fail-on-checks", action="store_true")

    args, rest = ap.parse_known_args()

    roots = resolve_dataset_roots()

    if args.cmd == "ingest-drumbeats":
        root = args.root or roots.drumbeats_root
        if not root:
            raise ValueError("missing --root (or DRUMBEATS_ROOT)")
        argv = []
        argv += ["--root", str(root)]
        if args.limit is not None:
            argv += ["--limit", str(int(args.limit))]
        import sys

        sys.argv = [sys.argv[0]] + argv + list(rest)
        return int(ingest_drumbeats_main())

    if args.cmd == "ingest-audio-phrases":
        argv = ["--root", str(args.root), "--dataset-id", str(args.dataset_id), "--label", str(args.label)]
        if args.limit is not None:
            argv += ["--limit", str(int(args.limit))]
        import sys

        sys.argv = [sys.argv[0]] + argv + list(rest)
        return int(ingest_audio_phrases_main())

    if args.cmd == "ingest-soundtracksloops":
        root = args.root or roots.soundtracksloops_root
        if not root:
            raise ValueError("missing --root (or SOUNDTRACKSLOOPS_ROOT)")
        argv = ["--root", str(root), "--dataset-id", "soundtracksloops", "--label", "SoundTracksLoops"]
        if args.limit is not None:
            argv += ["--limit", str(int(args.limit))]
        import sys

        sys.argv = [sys.argv[0]] + argv + list(rest)
        return int(ingest_audio_phrases_main())

    if args.cmd == "ingest-snare-rudiments":
        root = args.root or roots.snare_rudiments_root
        if not root:
            raise ValueError("missing --root (or SNARE_RUDIMENTS_ROOT)")
        argv = ["--root", str(root), "--dataset-id", "snare_rudiments", "--label", "Snare Rudiments"]
        if args.limit is not None:
            argv += ["--limit", str(int(args.limit))]
        import sys

        sys.argv = [sys.argv[0]] + argv + list(rest)
        return int(ingest_audio_phrases_main())

    if args.cmd == "ingest-transcription-artifacts":
        argv = ["--in", str(args.in_path), "--transcription-version", str(args.transcription_version)]
        if args.db_path:
            argv += ["--db-path", str(args.db_path)]
        if bool(getattr(args, "skip_missing_assets", False)):
            argv += ["--skip-missing-assets"]
        import sys

        sys.argv = [sys.argv[0]] + argv + list(rest)
        return int(ingest_transcription_artifacts_main())

    if args.cmd == "ingest-written-references":
        argv = [
            "--in",
            str(args.in_path),
            "--dataset-id",
            str(args.dataset_id),
            "--label",
            str(args.label),
            "--dataset-type",
            str(args.dataset_type),
            "--transcription-version",
            str(args.transcription_version),
            "--root-path",
            str(args.root_path),
            "--default-meter",
            str(args.default_meter),
            "--default-resolution-ppq",
            str(int(args.default_resolution_ppq)),
            "--default-subdiv",
            str(int(args.default_subdiv)),
        ]
        if args.db_path:
            argv += ["--db-path", str(args.db_path)]
        import sys

        sys.argv = [sys.argv[0]] + argv + list(rest)
        return int(ingest_written_references_main())

    if args.cmd == "datasets":
        db_path = getattr(args, "db_path", None)
        conn = dtkdb.connect(Path(str(db_path))) if db_path else dtkdb.connect()
        try:
            dtkdb.ensure_schema(conn)
            if args.datasets_cmd == "list":
                rows = dtkdb.list_datasets(conn)
                for r in rows:
                    print(json.dumps(r, ensure_ascii=False))
                return 0
            if args.datasets_cmd == "enable":
                dtkdb.set_dataset_enabled(conn, dataset_id=str(args.dataset_id), enabled=True)
                return 0
            if args.datasets_cmd == "disable":
                dtkdb.set_dataset_enabled(conn, dataset_id=str(args.dataset_id), enabled=False)
                return 0
            return 2
        finally:
            conn.close()

    if args.cmd == "flywheel-run":
        # Ensure a consistent DB target across all steps.
        if args.db_path:
            os.environ["DRUMMERBRAIN_DB_PATH"] = str(args.db_path)

        import sys

        if bool(getattr(args, "ingest_drumbeats", False)):
            argv = []
            root = roots.drumbeats_root
            if not root:
                raise ValueError("missing DRUMBEATS_ROOT")
            argv += ["--root", str(root)]
            sys.argv = [sys.argv[0]] + argv
            ingest_drumbeats_main()

        if getattr(args, "ingest_audio_phrases_root", None):
            dsid = getattr(args, "ingest_audio_phrases_dataset_id", None)
            lbl = getattr(args, "ingest_audio_phrases_label", None)
            if not dsid or not lbl:
                raise ValueError("--ingest-audio-phrases-dataset-id and --ingest-audio-phrases-label required")
            argv = [
                "--root",
                str(args.ingest_audio_phrases_root),
                "--dataset-id",
                str(dsid),
                "--label",
                str(lbl),
            ]
            if args.ingest_audio_phrases_limit is not None:
                argv += ["--limit", str(int(args.ingest_audio_phrases_limit))]
            sys.argv = [sys.argv[0]] + argv
            ingest_audio_phrases_main()

        if getattr(args, "ingest_written_refs_in", None):
            dsid = getattr(args, "ingest_written_refs_dataset_id", None)
            lbl = getattr(args, "ingest_written_refs_label", None)
            tv = getattr(args, "ingest_written_refs_transcription_version", None)
            if not dsid or not lbl or not tv:
                raise ValueError("--ingest-written-refs-dataset-id/--label/--transcription-version required")
            argv = [
                "--in",
                str(args.ingest_written_refs_in),
                "--dataset-id",
                str(dsid),
                "--label",
                str(lbl),
                "--transcription-version",
                str(tv),
            ]
            if args.db_path:
                argv += ["--db-path", str(args.db_path)]
            sys.argv = [sys.argv[0]] + argv
            ingest_written_references_main()

        if getattr(args, "import_artifacts_in", None):
            tv = getattr(args, "import_artifacts_transcription_version", None)
            if not tv:
                raise ValueError("--import-artifacts-transcription-version required")
            argv = ["--in", str(args.import_artifacts_in), "--transcription-version", str(tv)]
            if args.db_path:
                argv += ["--db-path", str(args.db_path)]
            if bool(getattr(args, "import_artifacts_skip_missing_assets", False)):
                argv += ["--skip-missing-assets"]
            sys.argv = [sys.argv[0]] + argv
            ingest_transcription_artifacts_main()

        argv = ["--out", str(args.out)]
        if args.db_path:
            argv += ["--db-path", str(args.db_path)]
        if args.cases_path:
            argv += ["--cases-path", str(args.cases_path)]
        if args.baseline:
            argv += ["--baseline", str(args.baseline)]
        if bool(getattr(args, "fail_on_checks", False)):
            argv += ["--fail-on-checks"]
        sys.argv = [sys.argv[0]] + argv
        return int(eval_harness_main())

    if args.cmd == "eval":
        argv = []
        if args.db_path:
            argv += ["--db-path", str(args.db_path)]
        if args.cases_path:
            argv += ["--cases-path", str(args.cases_path)]
        argv += ["--out", str(args.out)]
        if args.limit_cases is not None:
            argv += ["--limit-cases", str(int(args.limit_cases))]
        if args.baseline:
            argv += ["--baseline", str(args.baseline)]
        if bool(getattr(args, "fail_on_checks", False)):
            argv += ["--fail-on-checks"]
        import sys

        sys.argv = [sys.argv[0]] + argv + list(rest)
        return int(eval_harness_main())

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
