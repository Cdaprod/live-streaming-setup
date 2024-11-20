import unittest
from submodules.auto_fix_mobile import auto_fix_mobile_portrait
from models import VideoMetadata

class TestAutoFixMobile(unittest.TestCase):
    def test_auto_fix_mobile_success(self):
        video = VideoMetadata(
            video_id="12345",
            title="Test Video",
            input_path="/path/to/video.mp4",
        )
        result = auto_fix_mobile_portrait(video)
        self.assertTrue(result.success)
        self.assertIn("fixed", result.output_path)

if __name__ == "__main__":
    unittest.main()