import json
import os
from lib.clock_logging import logger

class LocalJsonIO():
    file_path = 'cache/context.json'
    
    def write_json_ctx(self, ctx=None, use_right_side=False):
        """
        Updates context.json with the ctx of left or right users.
        """
        # Try load existing data into context_data
        context_data = self.read_json_ctx(full_json=True)
        if not context_data:
            context_data = {'context': []}

        # Update data
        if use_right_side:
            context_data['context'].append({
                'position': 'right',
                'type': ctx[0],
                'title': ctx[1]
            })
        else:
            context_data['context'].append({
                'position': 'left',
                'type': ctx[0],
                'title': ctx[1]
            })

        # Write updated data
        try:
            with open(self.file_path, 'w+', encoding='utf-8') as j_cxt:
                json.dump(context_data, j_cxt)
        except (FileNotFoundError, PermissionError) as e:
            logger.error("error writing cache/context.txt -> %s", e)

    def read_json_ctx(self, use_right_side=False, full_json=False):
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
                        json_ctx = json_ctx['context']
                        json_ctx = json_ctx[1] if use_right_side else json_ctx[0]
                        return json_ctx['type'], json_ctx['title']
                except json.JSONDecodeError as e:
                    side = "right" if use_right_side else "left"
                    logger.error("error reading cache/context.txt for %s side-> %s", side, e)
        return None, None