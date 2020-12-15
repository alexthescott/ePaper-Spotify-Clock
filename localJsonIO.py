""" localJsonIO.py by Alex Scott 2020
Companion functions for mainSpotifyEPD.py

In this file, the two functions allow us to read and write 
to a local text file, holding json data representing the most 
recent context (ctx_type, ctx_name) from spotify

This was done becasue the Spotify API request can provide no context
given that a user starts a radio station, and other anomolostic spotify
events. This ensures that our program always knows the most recent context
"""

import json

def write_json_ctx(left_ctx, right_ctx):
    # if we have already written context info, don't rewrite file
    left_temp_ctx, right_tmp_ctx = left_ctx, right_ctx
    try:
        with open('context.txt') as j_ctx:
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
            print("Update context.txt")
            print("left_ctx: {} right_ctx: {}".format(left_ctx, right_ctx))
    except Exception as e:
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

    with open('context.txt', 'w+') as j_cxt:
        json.dump(context_data, j_cxt)

def read_json_ctx(left_ctx, right_ctx):
    with open('context.txt') as j_cxt:
        context_data = json.load(j_cxt)
        data = context_data['context']
        # Only update an empty context side. Either update the left ctx, the right ctx, or both ctx files
        if left_ctx[0] != "" and left_ctx[1] != "" and right_ctx[0] == "" and right_ctx[1] == "":
            return left_ctx[0], left_ctx[1], data[1]['type'], data[1]['title']
        elif left_ctx[0] == "" and left_ctx[1] == "" and right_ctx[0] != "" and right_ctx[1] !="":
            return data[0]['type'], data[0]['title'], right_ctx[0], right_ctx[1]
        else:
            return data[0]['type'], data[0]['title'], data[1]['type'], data[1]['title']
