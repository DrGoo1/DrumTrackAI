import unittest


class TestDrummerBrainManifestValidation(unittest.TestCase):
    def test_validate_written_reference_record_rejects_missing_grid_fields(self):
        from backend.drummerbrain.manifest import ManifestError, validate_written_reference_record

        with self.assertRaises(ManifestError):
            validate_written_reference_record({"clip_id": "x", "events": [{"barIndex": 0}]})

    def test_validate_transcription_artifact_record_rejects_bad_subdiv(self):
        from backend.drummerbrain.manifest import ManifestError, validate_transcription_artifact_record

        with self.assertRaises(ManifestError):
            validate_transcription_artifact_record(
                {
                    "asset_id": "ds:1",
                    "events": [{"beat_index": 0, "sub": 0, "subdiv": 0, "lane": "kick"}],
                }
            )
