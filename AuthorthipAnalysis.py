# Import required libraries, etc.
import sys
import os
import collections
import random
import re
import math
from dotenv import load_dotenv
import tweepy
import nltk


###
# This function prepares to use the Twitter API.
# Use "tweepy" to simplify the use of the API.
# Environment variables must be defined in the ".env" file.
###
def setup_twitter_api():
    load_dotenv()

    API_KEY = os.environ.get("API_KEY")
    API_KEY_SECRET = os.environ.get("API_KEY_SECRET")
    BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
    ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
    ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET")

    client = tweepy.Client(consumer_key = API_KEY,
                           consumer_secret = API_KEY_SECRET,
                           bearer_token = BEARER_TOKEN,
                           access_token = ACCESS_TOKEN,
                           access_token_secret = ACCESS_TOKEN_SECRET)

    return client


def get_tokenized_text(original_text):
    tokenizer = nltk.tokenize.RegexpTokenizer(r'\w+')
    return tokenizer.tokenize(original_text)


###
# This class performs Authorship Verification.
###
class AuthorshipVerifier:

    client = None
    author_names = list()
    tweet_texts_by_author = collections.defaultdict(lambda: list())
    known_texts_by_author = dict()
    questioned_texts_by_author = dict()
    ngram_count_by_author = dict()
    each_word_occurrence_rate_by_author = dict()
    questioned_texts_analysis_result = list()
    known_texts_for_compare_questioned_texts = list()

    ngram_numbers = [1, 2, 3]

    def __init__(self, client, user_name_1, user_name_2):
        self.client = client
        self.author_names = [user_name_1, user_name_2]

        self.create_tweet_texts_by_author()

        self.divide_questioned_texts_and_known_texts()

        self.create_ngram_count_by_author()

        self.create_each_word_occurrence_rate_by_author()

    def create_tweet_texts_by_author(self):
        for author_name in self.author_names:
            user_id = self.client.get_user(username = author_name).data.id

            pagination_token = None
            for i in range(20):
                tweets = self.client.get_users_tweets(id = user_id,
                                                 max_results = 100,
                                                 exclude = "retweets",
                                                 pagination_token = pagination_token)

                for tweet_data in tweets.data:
                    remove_url_text = re.sub(r"\S*https?:\S*", "", tweet_data["text"])
                    self.tweet_texts_by_author[author_name].append(remove_url_text)

                try:
                    pagination_token = tweets.meta["next_token"]
                except KeyError:
                    break

    def divide_questioned_texts_and_known_texts(self):
        for author_name in self.author_names:
            tweet_texts = self.tweet_texts_by_author[author_name]
            shuffled_tweet_texts = random.sample(tweet_texts, len(tweet_texts))

            known_text_count = int(len(shuffled_tweet_texts) * 0.9)

            known_texts = shuffled_tweet_texts[:known_text_count]
            questioned_texts = shuffled_tweet_texts[known_text_count:]

            self.known_texts_by_author[author_name] = known_texts
            self.questioned_texts_by_author[author_name] = questioned_texts

    def create_ngram_count_by_author(self):
        for author_name in self.author_names:
            self.ngram_count_by_author[author_name] = dict()

            for n in self.ngram_numbers:
                self.ngram_count_by_author[author_name][n] = collections.defaultdict(lambda: int())

                for known_text in self.known_texts_by_author[author_name]:
                    tokenized_text = get_tokenized_text(known_text)
                    for ngram in nltk.ngrams(tokenized_text, n):
                        self.ngram_count_by_author[author_name][n][ngram] += 1

    def create_each_word_occurrence_rate_by_author(self):
        for author_name in self.author_names:
            self.each_word_occurrence_rate_by_author[author_name] = collections.defaultdict(lambda: float())

            word_count_sum = sum(self.ngram_count_by_author[author_name][1].values())

            for word, word_count in self.ngram_count_by_author[author_name][1].items():
                word_occurrence = word_count / word_count_sum
                self.each_word_occurrence_rate_by_author[author_name][word] = word_occurrence

    def analysis(self):
        self.create_questioned_texts_analysis_result()

        self.create_known_texts_for_compare_questioned_texts()

        self.compare_author_of_questioned_text_and_known_text()

        self.print_accuracy()

    def create_questioned_texts_analysis_result(self):
        for question_author_name in self.author_names:
            for questioned_text in self.questioned_texts_by_author[question_author_name]:
                score_dict = collections.defaultdict(lambda: int())
                tokenized_text = get_tokenized_text(questioned_text)
                for n in self.ngram_numbers:
                    for ngram in nltk.ngrams(tokenized_text, n):
                        for known_author_name in self.author_names:
                            score_dict[known_author_name] += self.ngram_count_by_author[known_author_name][n][ngram] * math.pow(50, n - 1)

                author_1_total_word_count = sum(self.ngram_count_by_author[self.author_names[0]][1].values())
                author_2_total_word_count = sum(self.ngram_count_by_author[self.author_names[1]][1].values())

                total_word_count_ratio = author_1_total_word_count / author_2_total_word_count
                score_dict[self.author_names[0]] /= total_word_count_ratio

                for known_author_name in self.author_names:
                    for word in nltk.ngrams(tokenized_text, 1):
                        score_dict[known_author_name] += self.each_word_occurrence_rate_by_author[known_author_name][word] * 100000

                result_author_name = max(score_dict.items(), key = lambda x: x[1])[0]

                is_collect_author = result_author_name == question_author_name

                questioned_text_analysis_result = (result_author_name, questioned_text, is_collect_author)

                self.questioned_texts_analysis_result.append(questioned_text_analysis_result)

    def create_known_texts_for_compare_questioned_texts(self):
        known_texts_info = list()

        for author_name in self.author_names:
            for known_text in self.known_texts_by_author[author_name]:
                known_texts_info.append((author_name, known_text))

        total_questioned_text_cnt = sum(len(questioned_texts) for questioned_texts in self.questioned_texts_by_author.values())

        self.known_texts_for_compare_questioned_texts = random.sample(known_texts_info, total_questioned_text_cnt)

    def compare_author_of_questioned_text_and_known_text(self):
        total_questioned_text_cnt = sum(len(questioned_texts) for questioned_texts in self.questioned_texts_by_author.values())
        same_author_count = 0

        print(f'There are {total_questioned_text_cnt} questioned text.')

        print()

        for i in range(total_questioned_text_cnt):
            known_text_info = self.known_texts_for_compare_questioned_texts[i]
            questioned_text_info = self.questioned_texts_analysis_result[i]

            pre_line = f'{i + 1})' + '-' * 500
            post_line = '-' * len(pre_line)

            print(pre_line)

            print("・Known text")
            print(known_text_info[1])

            print()

            print("・Questioned text")
            print(questioned_text_info[1])

            print()

            print("・Result")
            if known_text_info[0] == questioned_text_info[0]:
                print("Same author.")
                same_author_count += 1
            else:
                print("Different author.")

            print(post_line)

            print()

        print(f"{same_author_count} of {total_questioned_text_cnt} text is same author.")

        print()

    def print_accuracy(self):
        total_questioned_text_cnt = sum(len(questioned_texts) for questioned_texts in self.questioned_texts_by_author.values())
        correct_author_cnt = len(list(filter(lambda question_text_info: question_text_info[2] is True, self.questioned_texts_analysis_result)))

        print(f"Accuracy: {correct_author_cnt / total_questioned_text_cnt * 100} %")


# Main process of the program
def main(args):

    if len(args) != 3:
        print("Please enter two Twitter usernames.")
        exit()

    user_name_1 = args[1]
    user_name_2 = args[2]

    print(f'author 1: @{user_name_1}')
    print(f'author 2: @{user_name_2}')

    print()

    client = setup_twitter_api()

    print("Creating verifier...")
    print()

    authorshipVerifier = AuthorshipVerifier(client, user_name_1, user_name_2)

    authorshipVerifier.analysis()


main(sys.argv)
