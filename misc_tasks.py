import csv

from invoke import task

__all__ = ['generate_anki_flashcards']


@task
def generate_anki_flashcards(ctx):
    def get_items():
        with open('item_location.csv') as fp:
            yield from csv.DictReader(fp)

    with open('flashcards.txt', 'w') as fp:
        count = 0
        for item in get_items():
            front = item['Model']
            back_list = [item['Location'], item['Title']]
            if item['Notes']:
                back_list.append('Notes: ' + item['Notes'])
            fp.write('{}\t{}\n'.format(front, '<br>'.join(back_list)))
            count += 1

        print('Wrote {} flashcards to flashcards.txt'.format(count))
