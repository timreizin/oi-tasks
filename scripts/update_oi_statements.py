from peolymp import AtlasAPI, TypeWriterAPI
import json
import os
import hashlib

import requests

SPACE_ID = os.environ["SPACE_ID"]
USERNAME = os.environ["EOLYMP_USERNAME"]
PASSWORD = os.environ["EOLYMP_PASSWORD"]

api = AtlasAPI(space_id=SPACE_ID, username=USERNAME, password=PASSWORD)
tw = TypeWriterAPI(space_id=SPACE_ID, username=USERNAME, password=PASSWORD)

folder_dir = os.path.join(os.path.dirname(__file__), '..')


def get_problem_sources():
    problems = api.get_problems()
    sources = {}
    for problem in problems:
        problem_id = problem.id
        statements = api.get_statements(problem_id)
        en = None
        for statement in statements:
            if statement.locale == "en":
                en = statement
        sources[en.source] = sources.get(en.source, []) + [problem_id]
    print('Sources')
    print(sources)
    return sources


def get_languages():
    with open(os.path.join(folder_dir, 'languages.json'), 'r') as f:
        languages = json.load(f)
    print('Languages')
    print(languages)
    return languages


def get_statements_from_folder(walk_path):
    statements = {}
    for (dir_path, dir_names, filenames) in os.walk(walk_path):
        for filename in filenames:
            if filename == ".DS_Store":
                continue
            name = filename.split('-')[-1]
            language = name[0:2]
            country = name[3:6]
            statements[language] = statements.get(language, []) + [(country, filename)]
    print('Statements from folder')
    print(statements)
    return statements


def get_statements(languages, walk_path):
    folder_statements = get_statements_from_folder(walk_path)
    statements = {}
    for lang in folder_statements:
        if len(folder_statements[lang]) == 1:
            ind = 0
        else:
            found = False
            for country in languages[lang]:
                for i in range(len(folder_statements[lang])):
                    if folder_statements[lang][i][0] == country:
                        found = True
                        ind = i
                        break
                if found:
                    break
        path = os.path.join(walk_path, folder_statements[lang][ind][1])
        statements[lang] = path
    print('Statements')
    print(statements)
    return statements


def get_link_from_file(path):
    name = path[path.rfind('/') + 1:]
    in_file = open(path, "rb")
    data = in_file.read()
    in_file.close()
    return tw.upload_asset(name, data)


def get_hash_of_file(path):
    in_file = open(path, "rb")
    data = in_file.read()
    in_file.close()
    return hashlib.sha256(data).hexdigest()


def update_eolymp_statements(prob_id, eolymp_statements, folder_statements):
    en = None
    for statement in eolymp_statements:
        locale = statement.locale
        print('Working on', locale)
        if locale == 'en':
            en = statement
        if locale in folder_statements:
            path = folder_statements[locale]
            folder_hash = get_hash_of_file(path)
            eolymp_statement_name = ''
            if not hasattr(statement, 'download_link') or statement.download_link == '':
                eolymp_hash = ''
            else:
                s = requests.get(statement.download_link)
                eolymp_statement_name = s.headers['Content-Disposition'].split('"')[1]
                eolymp_hash = hashlib.sha256(s.content).hexdigest()
            folder_statement_name = path.split('/')[-1]
            if folder_hash != eolymp_hash or eolymp_statement_name != folder_statement_name:
                statement.download_link = get_link_from_file(path)
                print('Updating')
                api.update_statement(prob_id, statement)
            folder_statements[locale] = None
        else:
            # TODO DELETE ENGL - delete
            print('!', prob_id, statement.id)
            exit(1)
            # if not engl api.delete_statement(prob_id, eolymp_language.id)

    for lang in folder_statements:
        if folder_statements[lang] is not None:
            print('Uploading', lang)
            api.create_statement(prob_id, lang, en.title, get_link_from_file(folder_statements[lang]), en.source)


def run_script():
    sources = get_problem_sources()
    all_languages = get_languages()

    for source in list(sources)[-2:]: #TEMP, Last 2 only
        temp = source.split(' ')
        if len(temp) != 2:
            continue
        if len(temp[1]) != 4:
            continue
        olymp = temp[0]
        year = temp[1]

        for i in range(len(sources[source])):
            if olymp == 'IOI' and year == '2012':
                prob_ind = max(1, i - 3)
            else:
                prob_ind = i + 1
            prob_id = sources[source][i]
            print(prob_id)
            walk_path = os.path.join(folder_dir, 'statements', olymp.lower(), year, str(prob_ind))
            folder_statements = get_statements(all_languages, walk_path)
            eolymp_statements = api.get_statements(prob_id)
            update_eolymp_statements(prob_id, eolymp_statements, folder_statements)
    print('done')


if __name__ == "__main__":
    run_script()

