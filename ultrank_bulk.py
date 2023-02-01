from ultrank_tiering import calculate_tier, startgg_slug_regex
import csv
import os 
import sys

true_values = ['true', 't', '1']

if __name__ == '__main__':
    # Get file
    file = input('input file to read keys from: ')

    if not os.path.exists(file):
        print('file doesn\'t exist!')
        sys.exit()

    # Read in values
    slugs = []

    _, ext = os.path.splitext(file)

    if ext == 'csv':
        with open(file, newline='') as file_obj:
            reader = csv.reader(file_obj)

            for row in reader:
                slug = row[0]

                if len(row) > 1:
                    is_invit = row[1].lower() in true_values
                else:
                    is_invit = False

                slugs.append({'slug': slug, 'invit': is_invit})
    else:
        with open(file) as file_obj:
            for row in file_obj:
                slugs.append({'slug': row.strip(), 'invit': False})

    print('read values')

    # Get values
    results = []

    for slug_obj in slugs:
        slug = slug_obj['slug']
        invit = slug_obj['invit']

        if startgg_slug_regex.fullmatch(slug):
            print('calculating for slug {}'.format(slug))

            try:
                result = calculate_tier(slug, invit)

                results.append({'slug': slug, 'result': result})
            except Exception as e:
                print(e)
                results.append({'slug': slug, 'result': None})
        else:
            print('skipping slug {}'.format(slug))
            results.append({'slug': slug, 'result': None})

    # Write CSV
    if not os.path.isdir('tts_values'):
        os.mkdir('tts_values')

    print('writing summary file')

    with open('tts_values/summary.csv', newline='', mode='w') as summary_file:
        writer = csv.writer(summary_file)
        writer.writerow(['Slug', 'Score', 'Max Potential Score', 'Num Entrants'])

        for result in results:
            if result['result'] == None:
                writer.writerow([result['slug'], '', '', ''])
            else:
                writer.writerow([result['slug'], result['result'].score, result['result'].max_potential_score(), result['result'].entrants])

    # Write values

    for result in results:
        if result['result'] == None:
            continue

        print('writing for slug {}'.format(result['slug']))

        with open('tts_values/{}.txt'.format(result['slug'].replace('/', '_')), mode='w') as write_file:
            result['result'].write_result(write_file)
