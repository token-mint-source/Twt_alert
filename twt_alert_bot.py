import os
import smtplib
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect
import tweepy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Initialize Twitter client
client = tweepy.Client(bearer_token=os.getenv('BEARER_TOKEN'))

# Store keywords in memory (consider using database in production)
keywords = set()

class AlertStream(tweepy.StreamingClient):
    def on_tweet(self, tweet):
        if not tweet.text.startswith('RT'):  # Exclude retweets
            self.send_alert(tweet)
    
    def send_alert(self, tweet):
        msg = EmailMessage()
        msg.set_content(f"New tweet matching your keywords:\n\n{tweet.text}\n\nhttps://twitter.com/user/status/{tweet.id}")
        msg['Subject'] = "Twitter Keyword Alert!"
        msg['From'] = os.getenv('EMAIL_USER')
        msg['To'] = os.getenv('EMAIL_USER')
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASSWORD'))
            smtp.send_message(msg)

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
    stream.rules.delete(stream.get_rules().data)  # Clear existing rules
    if keywords:
        stream.add_rules(tweepy.StreamRule(" OR ".join(keywords)))

if __name__ == '__main__':
    update_stream()
    stream.filter()
    app.run(debug=False)
