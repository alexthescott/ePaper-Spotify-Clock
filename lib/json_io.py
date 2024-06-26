import json
import os
from lib.clock_logging import logger

class LocalJsonIO:
    """
    A class for reading and writing Spotify Listening JSON data to a local file.
    """
    file_path = 'cache/context.json'

    def write_json_ctx(self, ctx: dict = None, use_right_side: bool = False) -> None:
        """
        Updates context.json with the ctx of left or right users.
        """
        context_data = self.read_json_ctx(full_json=True) or {'context': [{'position': 'right'}, {'position': 'left'}]}

        position = 'right' if use_right_side else 'left'
        ctx['position'] = position
        context_data['context'] = [c for c in context_data['context'] if c['position'] != position]
        context_data['context'].append(ctx)

        try:
            with open(self.file_path, 'w+', encoding='utf-8') as j_cxt:
                json.dump(context_data, j_cxt, indent=4)
        except (FileNotFoundError, PermissionError) as e:
            logger.error("error writing cache/context.txt -> %s", e)

    def read_json_ctx(self, use_right_side: bool = False, full_json: bool = False) -> dict:
        """
        Read context.txt, returning ctx found if left_ctx, or right_ctx is empty. 
        """
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as j_cxt:
                try:
                    json_ctx = json.load(j_cxt)
                    if full_json:
                        return json_ctx
                    if json_ctx:
                        position = 'right' if use_right_side else 'left'
                        return next((item for item in json_ctx['context'] if item['position'] == position), None)
                except (json.JSONDecodeError, IndexError) as e:
                    logger.error("error reading cache/context.txt for %s side-> %s", position, e)
        return None
