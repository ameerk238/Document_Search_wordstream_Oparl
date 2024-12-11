from flask import Flask, render_template, request, jsonify, Response, send_file
from elasticsearch import Elasticsearch
from wordcloud_generator import WordCloud
import io
import calendar
import re
import nltk
from nltk.corpus import stopwords

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from sklearn.feature_extraction.text import TfidfVectorizer

from wordcloud_generator import generate_word_cloud



app = Flask(__name__)
es = Elasticsearch(['http://localhost:9200'])  # Replace with your Elasticsearch server details

# Download and get German stopwords
nltk.download('punkt')
nltk.download('stopwords')
german_stopwords = list(stopwords.words('german'))

# Additional stopwords to exclude from the word cloud
additional_stopwords = ["vorlage", "antrag", "seite", "sitzung", "sei", "abs"]

# Combine the stopwords
german_stopwords += additional_stopwords

def clean_text(text):
    # Remove HTML tags
    text = re.sub(r'<.*?>', '', text)
    
    # Keep only ASCII + European characters and whitespace, excluding digits
    text = re.sub(r'[^A-Za-zäöüÄÖÜß\s]', '', text)
    
    # Remove single-letter characters
    text = re.sub(r'\b\w\b', '', text)
    
    # Convert to lowercase
    text = text.lower()
    
    
    text = ' '.join([word for word in text.split() if word not in german_stopwords])
    
    return text

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.json.get('query')
    page = request.json.get('page', 1)  # Default to page 1 if not provided
    size = 10  # Number of documents per page
    from_ = (page - 1) * size  # Calculate the starting point
    if query:
        # Using query_string for a broader search across all fields
        body = {
            'from': from_,
            'size': size,
            'query': {
                'query_string': {
                    'query': query
                }
            }
        }

        result = es.search(index='agendaitem_content', body=body)
        hits = result['hits']['hits']

        search_results = ''
        count = result['hits']['total']['value']  # Get the total count of matched documents
        if count:
            # Added this block for feedback
            if count > 10:
                search_results += f"<p><strong>{count} documents were found in the search. Displaying top 10...</strong></p>"
            else:
                search_results += f"<p><strong>{count} documents were found in the search:</strong></p>"

        for index, hit in enumerate(hits):
            # Extracting participants' names
            participants = hit['_source'].get('participant', [])
            participant_names = [p['person_name'] for p in participants if 'person_name' in p]
            participant_names_str = ', '.join(participant_names)

            # Extract auxiliary file details
            auxiliary_files = hit['_source'].get('auxiliaryFile', [])
            auxiliary_file_details = ""
            for file in auxiliary_files:
                auxiliary_file_name = file.get('auxiliaryfile_name', 'Not Available')
                auxiliary_file_downloadurl = file.get('auxiliaryfile_downloadurl', 'Not Available')
                auxiliary_file_link = f"<a href='{auxiliary_file_downloadurl}' target='_blank'>{auxiliary_file_name}</a>"
                auxiliary_file_details += f"<div><strong>Auxiliary File:</strong> {auxiliary_file_link}</div>"

            # Extract results protocol details
            results_protocol = hit['_source'].get('resultsProtocol', {})
            results_protocol_name = results_protocol.get('results_protocol_name', 'Not Available')
            results_protocol_downloadurl = results_protocol.get('results_protocol_downloadurl', 'Not Available')
            results_protocol_link = f"<a href='{results_protocol_downloadurl}' target='_blank'>{results_protocol_name}</a>"


            documentNumber = (page - 1) * size + index + 1
            search_results += f"""
            <div class='document'>
                <strong>{documentNumber}. {hit['_source']['agendaitem_name']}</strong>
                <div><strong>Meeting Name:</strong> {hit['_source'].get('meeting_name', 'Not Available')}</div>
                <div><strong>Meeting Start:</strong> {hit['_source'].get('meeting_start', 'Not Available')}</div>
                <div><strong>Meeting Location:</strong> {hit['_source'].get('meeting_room', 'Not Available')}</div>
                <div><strong>Organization:</strong> {hit['_source'].get('organisation_name', 'Not Available')}</div>
                <div><strong>Participants:</strong> {participant_names_str or 'Not Available'}</div>
                {auxiliary_file_details}
                <div><strong>Results Protocol:</strong> {results_protocol_link}</div>
            </div>
            """

        return Response(search_results, content_type='text/html')

    return jsonify('')

@app.route('/search-count', methods=['POST'])
def search_count():
    query = request.json.get('query')
    if query:
        body = {
            'query': {
                'query_string': {
                    'query': query
                }
            }
        }
        result = es.search(index='agendaitem_content', body=body)
        count = result['hits']['total']['value']
        return jsonify(count)
    return jsonify(0)

@app.route('/generate-word-cloud', methods=['POST'])
def generate_word_cloud_route():
    date = request.json.get('date')

    if date == "2022":  # Check if the entire year is selected
        start_date = "2022-01-01T00:00:00"
        end_date = "2022-12-31T23:59:59"

    else:
        year, month = 2022, int(date.split('-')[1])
        month_str = str(month).zfill(2)
        start_date = f"{year}-{month_str}-01T00:00:00"
        end_date = f"{year}-{month_str}-{calendar.monthrange(year, month)[1]}T23:59:59"

    query_body = {
        "query": {
            "range": {
                "meeting_start": {
                    "gte": start_date,
                    "lte": end_date
                }
            }
        }
    }

    results = es.search(index='agendaitem_content', body=query_body, size=10000)
    hits = results['hits']['hits']

    contents = []
    for hit in hits:
        auxiliary_files = hit['_source']['auxiliaryFile']
        results_protocol_content = hit['_source'].get('results_protocol_content', '')  # Extract results_protocol_content

        for file in auxiliary_files:
            if 'auxiliaryfile_content' in file:
                text_content = file['auxiliaryfile_content']
                cleaned_text = clean_text(text_content)
                contents.append(cleaned_text)
                
        # Add results_protocol_content to contents
        if results_protocol_content:
            cleaned_result_content = clean_text(results_protocol_content)
            contents.append(cleaned_result_content)

    img = generate_word_cloud(contents)

    return send_file(img, mimetype='image/png')



if __name__ == '__main__':
    app.run()