import os
import requests  # Add this import
from flask import Flask, render_template, request, redirect
import tweepy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Initialize Twitter client
client = tweepy.Client(bearer_token=os.getenv('BEARER_TOKEN'))

# Store keywords in memory
keywords = set()

class AlertStream(tweepy.StreamingClient):
    def on_tweet(self, tweet):
        if not tweet.text.startswith('RT'):  # Exclude retweets
            self.send_alert(tweet)
    
    def send_alert(self, tweet):
        # Telegram bot configuration
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        message = (
            f"🚨 New Twitter Alert!\n\n"
            f"📝 Content: {tweet.text}\n\n"
            f"🔗 Link: https://twitter.com/user/status/{tweet.id}"
        )
        
        # Send message to Telegram
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Telegram API Error: {e}")

# Initialize stream
stream = AlertStream(os.getenv('BEARER_TOKEN'))

@app.route('/')
def index():
    return render_template('index.html', keywords=keywords)

@app.route('/add', methods=['POST'])
def add_keyword():
    keyword = request.form['keyword'].strip().lower()
    if keyword:
        keywords.add(keyword)
        update_stream()
    return redirect('/')

@app.route('/remove/<keyword>')
def remove_keyword(keyword):
    keywords.discard(keyword)
    update_stream()
    return redirect('/')

def update_stream():
    # Clear existing rules first
    existing_rules = stream.get_rules()
    
    if existing_rules and existing_rules.data:
        rule_ids = [rule.id for rule in existing_rules.data]
        stream.delete_rules(rule_ids)

    # Add new rules if keywords exist
    if keywords:
        stream.add_rules([tweepy.StreamRule(" OR ".join(keywords))])

if __name__ == '__main__':
    update_stream()
    # Run stream and Flask app concurrently
    from threading import Thread
    Thread(target=stream.filter).start()
    app.run(debug=False)
