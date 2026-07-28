import unittest
import os

from arena.engine.admin import setup_game
from arena.engine.gamedirectory import GameDirectory
from arena.log import deactivate_logger_blocklist


class TestSVGGeneration(unittest.TestCase):
    def setUp(self):
        deactivate_logger_blocklist()
        self.test_dir = './test/test-games'

    def test_svg_generation(self):
        """Test that SVG files are generated alongside PNG files."""
        gd = GameDirectory(self.test_dir, 'test-game')
        game = setup_game(gd)
        
        # Run one round
        self.assertTrue(game.current_round_ready)
        game.process_current_round()
        
        # Check that both PNG and SVG files were created
        round_dir = game._dir.round_dir(1)
        ships = game._dir.load_status(0)  # Load initial ships
        
        for ship_name in ships.keys():
            png_file = f"{ship_name}-round-1.png"
            svg_file = f"{ship_name}-round-1.svg"
            
            # Verify PNG exists (original functionality)
            png_path = os.path.join(round_dir.full_name, png_file)
            self.assertTrue(os.path.exists(png_path), 
                          f"PNG file {png_file} should exist")
            
            # Verify SVG exists (new functionality)
            svg_path = os.path.join(round_dir.full_name, svg_file)
            self.assertTrue(os.path.exists(svg_path), 
                          f"SVG file {svg_file} should exist")
            
            # Verify SVG content is valid
            svg_content = round_dir.load(svg_file)
            self.assertTrue(svg_content.startswith('<svg'), 
                          f"SVG file {svg_file} should start with <svg tag")
            self.assertTrue('</svg>' in svg_content, 
                          f"SVG file {svg_file} should contain closing </svg tag")


if __name__ == '__main__':
    unittest.main()