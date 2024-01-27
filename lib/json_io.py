import json
from lib.clock_logging import logger

class LocalJsonIO():
    def write_json_ctx(self, left_ctx, right_ctx):
        """
        Creates, writes to context.txt a json object containing the ctx of left and right users.
        """

        # if we have already written context info, don't rewrite file
        left_temp_ctx, right_tmp_ctx = left_ctx, right_ctx
        try:
            with open('cache/context.txt', encoding='utf-8') as j_ctx:
                write_l_ctx, write_r_ctx = True, True
                data = json.load(j_ctx)

                # check left ctx, assign tmp ctx if our pulled data is new
                if left_ctx[0] == data['context'][0]['type'] and left_ctx[1] == data['context'][0]['title']:
                    write_l_ctx = False
                # check right ctx, assign tmp ctx if our pulled data is new
                if right_ctx[0] == data['context'][1]['type'] and right_ctx[1] == data['context'][1]['title']:
                    write_r_ctx = False

                if not write_l_ctx and not write_r_ctx:
                    return
                logger.info("write_json_ctx() - left_ctx: %s right_ctx: %s", left_ctx, right_ctx)
        except (FileNotFoundError, PermissionError) as e:
            print("write_json_ctx() Failed:", e)
            print("writing to new context.txt")

        context_data = {}
        context_data['context'] = []
        # attach left ctx
        context_data['context'].append({
                'position': 'left',
                'type': left_temp_ctx[0],
                'title': left_temp_ctx[1]
        })
        # attach right ctx
        context_data['context'].append({
            'position': 'right',
            'type': right_tmp_ctx[0],
            'title': right_tmp_ctx[1]
        })

        with open('cache/context.txt', 'w+', encoding='utf-8') as j_cxt:
            json.dump(context_data, j_cxt)

    def read_json_ctx(self, left_ctx, right_ctx):
        """
        Read context.txt, returning ctx found if left_ctx, or right_ctx is empty. 
        """
        try:
            with open('cache/context.txt', 'w+', encoding='utf-8') as j_cxt:
                context_data = json.load(j_cxt)
                data = context_data['context']
                # Only update an empty context side. Either update the left ctx, the right ctx, or both ctx files
                if left_ctx[0] != "" and left_ctx[1] != "" and right_ctx[0] == "" and right_ctx[1] == "":
                    return left_ctx[0], left_ctx[1], data[1]['type'], data[1]['title']
                elif left_ctx[0] == "" and left_ctx[1] == "" and right_ctx[0] != "" and right_ctx[1] != "":
                    return data[0]['type'], data[0]['title'], right_ctx[0], right_ctx[1]
                else:
                    return data[0]['type'], data[0]['title'], data[1]['type'], data[1]['title']
        except (FileNotFoundError, PermissionError) as e:
            logger.info("read_json_ctx() Failed: %s", e)
            return "", "", "", ""
