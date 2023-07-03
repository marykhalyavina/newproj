from flask import Flask, request
from nltk.corpus import wordnet
import mimetypes
from difflib import SequenceMatcher
import sqlparse
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
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
                if word1.isalpha() and all(ord(c) < 128 for c in word1):
                    try:
                        word1.encode(
                            encoding='utf-8').decode('ascii')
                    except UnicodeDecodeError:
                        for r in range(0, len(words1)):
                            replacebool, char = check_russian_to_english_greek(
                                word1[r])
                        if replacebool:
                            phrase1 = phrase1.replace(
                                word1[r], char, 1)
                        break
                synonyms1 = find_synonyms(word1)
                for word2 in words2:
                    if word2.isalpha() and all(ord(c) < 128 for c in word2):
                        try:
                            word2.encode(
                                encoding='utf-8').decode('ascii')
                        except UnicodeDecodeError:
                            for r in range(0, len(words2)):
                                replacebool, char = check_russian_to_english_greek(
                                    word2[r])
                            if replacebool:
                                phrase2 = phrase2.replace(
                                    word2[r], char, 1)
                            break
                    if word2 in synonyms1:
                        phrase1 = phrase1.replace(
                            word1, word2, 1)
            similarity = fuzz.token_set_ratio(phrase1, phrase2)
            if similarity >= 60:
                if phrase1 not in common_phrases:
                    common_phrases.append(phrase1)
    return common_phrases


def calculate_plagiarism_percentage(common_phrases, text):
    total_words = text.lower().split()
    plagiarized_words = ' '.join(common_phrases).lower().split()
    plagiarism_percentage = (len(plagiarized_words) / len(total_words)) * 100
    if plagiarism_percentage > 100:
        plagiarism_percentage = 100
    return plagiarism_percentage


def getHtmlData(filename):
    file_type, _ = mimetypes.guess_type(filename)
    if file_type != 'text/html':
        return filename
    soup = BeautifulSoup(filename, 'html.parser')
    paragraphs = soup.find_all('p')
    text = ' '.join([p.text for p in paragraphs])
    return text


@app.route('/checkText', methods=['POST'])
def plagiarism_check():
    texts = request.json

    comparison_array = []
    for text in texts:
        comparison_array.append(getHtmlData(text))

    common_phrases = []
    for i in range(len(comparison_array) - 1):
        common_phrases.extend(find_common_phrases(
            comparison_array[0], comparison_array[i + 1]))

    if common_phrases:
        plagiarism_percentage = calculate_plagiarism_percentage(
            common_phrases, comparison_array[0])
        return f'{100 - plagiarism_percentage}%'
    else:
        return '100%'


if __name__ == '__main__':
    app.run()
