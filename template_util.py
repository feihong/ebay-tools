

def get_copy_text(items, item_map):
    "Return text to be copied and pasted onto shipping label."
    result = []
    for item in items:
        if item['quantity'] > 1:
            text = '{quantity}x {model}'.format(**item)
        else:
            text = item['model']

        item_dict = item_map.get(item['model'], None)
        if item_dict is not None:
            text += ' ' + item_dict['Location']
        else:
            text += ' ?'
        result.append(text)
    return ', '.join(result)


def get_additional_details(item, item_map):
    "Return a string containing additional details for an item."
    item_dict = item_map.get(item['model'], None)
    if item_dict is None:
      return None

    keys = ('Notes',)
    details = ((k, item_dict[k]) for k in keys)
    details = [(k, v) for k, v in details if v.strip()]
    if len(details):
      return '; '.join('%s: %s' % (k, v) for k, v in details)
    else:
      return None
