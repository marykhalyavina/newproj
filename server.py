from flask import Flask, request
from nltk.corpus import wordnet
from difflib import SequenceMatcher
import sqlparse
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
# from stop_words import get_stop_words

import nltk
nltk.download('wordnet')
nltk.download('omw-1.4')

app = Flask(__name__)


def find_synonyms(word):
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name())
    return synonyms


def check_russian_to_english_greek(char):
    russian_to_english = {'а': 'a', 'е': 'e', 'р': 'p', 'о': 'o', 'с': 'c', 'у': 'y', 'к': 'k', 'х': 'x', 'в': 'b',
                          'м': 'm', 'т': 't'}
    russian_to_greek = {'а': 'α', 'е': 'ε', 'р': 'ρ', 'о': 'ο', 'с': 'ς', 'у': 'υ', 'к': 'κ', 'х': 'χ', 'в': 'ν',
                        'м': 'μ', 'т': 'τ'}

    if char in russian_to_english.values():
        return True, list(russian_to_english.keys())[list(russian_to_english.values()).index(char)]
    elif char in russian_to_greek.values():
        return True, list(russian_to_greek.keys())[list(russian_to_greek.values()).index(char)]
    elif char in russian_to_english.keys():
        return False, russian_to_english[char]
    elif char in russian_to_greek.keys():
        return False, russian_to_greek[char]
    else:
        return True, char


# def remove_stopwords(word):
#    stop_words = set(wordnet.words("russian"))
#    return word.lower() in stop_words


def find_common_phrases(text1, text2):
    common_phrases = []
    phrases1 = text1.lower().split('.')
    phrases2 = text2.lower().split('.')

    for phrase1 in phrases1:
        words1 = phrase1.strip().split()
        for phrase2 in phrases2:
            words2 = phrase2.strip().split()
            for i in range(0, len(words1), 2):
                word1 = words1[i]
                # if remove_stopwords(word1):
                #    continue
                synonyms1 = find_synonyms(word1)
                for word2 in words2:
                    if word1 == word2 or word2 in synonyms1:
                        similarity = fuzz.token_set_ratio(phrase1, phrase2)
                        if similarity >= 70:
                            if word2.isalpha() and all(ord(c) < 128 for c in word2):
                                # Check if the word is in Russian
                                try:
                                    word2.encode(
                                        encoding='utf-8').decode('ascii')
                                except UnicodeDecodeError:
                                    # Word contains non-ASCII characters, assuming it is in Russian
                                    replace, char = check_russian_to_english_greek(
                                        word2[0])
                                    if replace:
                                        new_phrase = phrase2.replace(
                                            word2[0], char, 1)
                                    else:
                                        new_phrase = phrase2

                                    # Check if the new phrase is already present in common_phrases
                                    if new_phrase not in common_phrases:
                                        common_phrases.append(new_phrase)
                                    break
                            else:
                                # Word is not in Russian, directly process it
                                replace, char = check_russian_to_english_greek(
                                    word2[0])
                                if replace:
                                    new_phrase = phrase2.replace(
                                        word2[0], char, 1)
                                else:
                                    new_phrase = phrase2

                                # Check if the new phrase is already present in common_phrases
                                if new_phrase not in common_phrases:
                                    common_phrases.append(new_phrase)
                                break

    return common_phrases


def calculate_plagiarism_percentage(common_phrases, text):
    total_words = text.lower().split()
    plagiarized_words = ' '.join(common_phrases).lower().split()
    plagiarism_percentage = (len(plagiarized_words) / len(total_words)) * 100
    if (plagiarism_percentage > 100):
        plagiarism_percentage = 100

    # originality_percentage = len(text_safe) / len(text)
    # return originality_percentage * 100
    return plagiarism_percentage


def parse_sql(sql_code):
    parsed = sqlparse.parse(sql_code)
    return parsed[0] if parsed else None


def generate_parse_tree(sql_code):
    parsed = parse_sql(sql_code)
    return parsed.normalized if parsed else None


def calculate_similarity(tree1, tree2):
    if tree1 is None or tree2 is None:
        return 0.0
    matcher = SequenceMatcher(None, str(tree1), str(tree2))
    return matcher.ratio()


# def calculate_originality(sql_code, copied_sql_codes):
 #   parse_tree = generate_parse_tree(sql_code)
 #   if parse_tree is None:
 #       return 0.0
#
 #   similarity_scores = []
 #   for copied_code in copied_sql_codes:
 #       similarity = calculate_similarity(
#           parse_tree, generate_parse_tree(copied_code))
# if similarity not in similarity_scores:
#            similarity_scores.append(similarity)
##
#    if not similarity_scores:
#        return 100.0

#    average_similarity = len(similarity_scores) / len(sql_code)
 #   return average_similarity
    # originality = 100.0 - (average_similarity * 100.0)
    # return originality

def calculate_originality(sql_code, copied_sql_codes):
    parse_tree = generate_parse_tree(sql_code)
    if parse_tree is None:
        return 0.0

    similarity_scores = []
    for copied_code in copied_sql_codes:
        similarity = calculate_similarity(
            parse_tree, generate_parse_tree(copied_code))
        if similarity not in similarity_scores:
            similarity_scores.append(similarity)

    if not similarity_scores:
        return 100.0
    # sql_code_safe = sql_code
    # for similarity in sql_code_safe:
    #    sql_code_safe = sql_code_safe.replace(similarity, '')

    total_words = sql_code.lower().split()
    plagiarized_words = ' '.join(copied_sql_codes).lower().split()
    if len(plagiarized_words) > len(total_words):
        return 0
    plagiarism_percentage = (len(plagiarized_words) / len(total_words)) * 100
    return 100 - plagiarism_percentage
    # originality_percentage = len(sql_code_safe) / len(sql_code)
    # return originality_percentage * 100


def getHtmlData(filename):
    # Создание объекта BeautifulSoup
    soup = BeautifulSoup(filename, 'html.parser')
    paragraphs = soup.find_all('p')
    text = ' '.join([p.text for p in paragraphs])
    return text

# Функция для проверки плагиата


def check_plagiarism(text):
    comparison_array = []
    file_path = 'C:/Users/Masha/Downloads/1/'
    # Чтение содержимого файла
    with open(file_path + '1-00_3030895_assignsubmission_onlinetext_onlinetext.html', 'r') as file:
        html_doc = file.read()
    comparison_array.append(getHtmlData(html_doc))
    with open(file_path + 'Бородинов Александр Андреевич ИТб-4301-01-00_2010273_assignsubmission_onlinetext_onlinetext.html', 'r') as file:
        html_doc = file.read()
    comparison_array.append(getHtmlData(html_doc))
    with open(file_path + 'Бронников Александр Васильевич ИТб-2301-01-00_3776055_assignsubmission_onlinetext_onlinetext.html', 'r') as file:
        html_doc = file.read()
    comparison_array.append(getHtmlData(html_doc))
    common_phrases = []
    for comparison_text in comparison_array:
        common_phrases.extend(find_common_phrases(text, comparison_text))

    if common_phrases:
        plagiarism_percentage = calculate_plagiarism_percentage(
            common_phrases, text)
        return plagiarism_percentage
    else:
        return 0

# Маршрут для обработки POST-запроса


@app.route('/checkText', methods=['POST'])
def plagiarism_check():
    # Получаем текст из POST-запроса
    text = request.form.get('text')

    # Выполняем проверку плагиата
    plagiarism_check = check_plagiarism(text)

    # Возвращаем результаты проверки плагиата
    return f'Оригинальность: {100 - plagiarism_check}'


copied_sql_codes = [
    "SELECT * FROM customers WHERE age > 30",
    "SELECT * FROM customers WHERE age < 40",
    "SELECT * FROM orders WHERE total_price > 100",
    "INSERT INTO customers (name, age) VALUES ('John Doe', 35)",
]
# Маршрут для обработки POST-запроса


@app.route('/checkSQL', methods=['POST'])
def plagiarism_checkSQL():
    # Получаем текст из POST-запроса
    sql_code = request.form.get('text')

    # Выполняем проверку плагиата
    originality_sql = calculate_originality(sql_code, copied_sql_codes)

    # Возвращаем результаты проверки плагиата
    return f'Оригинальность: {originality_sql}'


@app.route('/')
def hello():
    return 'Для проверки на плагиат перейди по ссылке http://127.0.0.1:5000/checkText'


if __name__ == '__main__':
    app.run()
