import importlib.util
from pathlib import Path
import unittest

BASE=Path(__file__).resolve().parents[1]

def module_from(path, name):
    spec=importlib.util.spec_from_file_location(name,BASE/path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

FULL=module_from('rpi4_fullchip.py','fullchip')
COMP=module_from('comparar.py','fullchip_comparator')

class RendererTests(unittest.TestCase):
    def test_v3d_accepted(self):
        ok, renderer=FULL.gpu_hw_renderer('GL_RENDERER: V3D 4.2.14.0')
        self.assertTrue(ok)
        self.assertEqual(renderer,'V3D 4.2.14.0')
    def test_software_rejected(self):
        for name in ['llvmpipe','softpipe','swrast','Software Rasterizer']:
            with self.subTest(name=name):
                ok,_=FULL.gpu_hw_renderer('GL_RENDERER: '+name)
                self.assertFalse(ok)
    def test_renderer_missing(self):
        ok,_=FULL.gpu_hw_renderer('Frames rendered: 10')
        self.assertFalse(ok)

class ComparatorTests(unittest.TestCase):
    def test_stage_count(self):
        self.assertEqual(len(COMP.STAGES),5)
        self.assertEqual(set(COMP.STAGES),set(FULL.STAGES))
    def test_series_coordinates(self):
        rows=[{'stage':'cpu_single','freq_target_mhz':'1500','temperature_c':'42.0','phase':'repouso','elapsed_s':'0'},
              {'stage':'cpu_single','freq_target_mhz':'1500','temperature_c':'48.0','phase':'stress','elapsed_s':'2'},
              {'stage':'cpu_single','freq_target_mhz':'1500','temperature_c':'44.0','phase':'resfriamento','elapsed_s':'1'}]
        pts,splits=COMP.series_points(rows,'cpu_single',1500)
        self.assertEqual(len(pts),3)
        self.assertEqual(len(splits),2)
        self.assertEqual(pts[0][1],42.0)

if __name__=='__main__': unittest.main()
