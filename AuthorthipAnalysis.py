# Import required libraries, etc.
import sys
import os
import collections
from dotenv import load_dotenv
import tweepy


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


###
# This class performs Authorship Verification.
###
class AuthorshipVerifier:
    tweet_texts_by_author = collections.defaultdict(lambda: list())

    def __init__(self, client, user_name_1, user_name_2):
        for user_name in [user_name_1, user_name_2]:
            user_id = client.get_user(username = user_name).data.id

            pagination_token = None
            for i in range(20):
                tweets = client.get_users_tweets(id = user_id,
                                                 max_results = 100,
                                                 exclude = "retweets",
                                                 pagination_token = pagination_token)

                for tweet_data in tweets.data:
                    self.tweet_texts_by_author[user_name].append(tweet_data["text"])

                pagination_token = tweets.meta["next_token"]


# Main process of the program
def main(args):

    if len(args) != 3:
        print("Please enter two Twitter usernames.")
        exit()

    user_name_1 = args[1]
    user_name_2 = args[2]

    client = setup_twitter_api()

    authorshipVerifier = AuthorshipVerifier(client, user_name_1, user_name_2)


main(sys.argv)
