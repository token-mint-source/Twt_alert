import os
import requests
from flask import Flask, render_template, request, redirect
import tweepy
from dotenv import load_dotenv
from threading import Thread

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

def update_stream():
    """Update Twitter stream rules based on current keywords"""
    # Clear existing rules first
    existing_rules = stream.get_rules()
    
    if existing_rules and existing_rules.data:
        rule_ids = [rule.id for rule in existing_rules.data]
        stream.delete_rules(rule_ids)

    # Add new rules if keywords exist
    if keywords:
        stream.add_rules([tweepy.StreamRule(" OR ".join(keywords))])

# Routes
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

if __name__ == '__main__':
    # Initial setup
    update_stream()
    
    # Start Twitter stream in a separate thread
    Thread(target=stream.filter).start()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
