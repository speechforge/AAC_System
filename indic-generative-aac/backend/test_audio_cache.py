import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import audio_cache as cache
class AudioCacheTest(unittest.TestCase):
 def test_disk_hit_clear_and_language_isolation(self):
  with tempfile.TemporaryDirectory() as directory,patch.object(cache,'ROOT',Path(directory)),patch.object(cache,'CACHE',Path(directory)/'cache'):
   config={'engine':'indicf5'};audio=np.array([100,-100,200],dtype=np.int16)
   self.assertIsNone(cache.load('water','en',config));cache.save('water','en',config,audio,24000)
   got,sr=cache.load('water','en',config);self.assertEqual(sr,24000);self.assertTrue(np.array_equal(got,audio))
   self.assertIsNone(cache.load('water','gu',config));self.assertEqual(cache.clear()['removed'],1);self.assertIsNone(cache.load('water','en',config))
if __name__=='__main__':unittest.main()
