from flask import Flask, request, send_file, jsonify, render_template, Response
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import zipfile

app = Flask(__name__, template_folder='templates')

# Fungsi untuk mendapatkan hasil dari Google Suggest
def get_google_suggest(query):
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={query}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()[1]
    return []

# Fungsi untuk mendapatkan long-tail keywords dari Google Suggest
def get_long_tail_keywords(base_keyword):
    long_tail_suggestions = get_google_suggest(base_keyword)
    return long_tail_suggestions

# Fungsi untuk mendapatkan People Also Ask dari Google Search
def get_people_also_ask(query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    url = f"https://www.google.com/search?q={query}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        paa = soup.select("div.related-question-pair span")
        unique_paa = list(set(item.get_text(strip=True) for item in paa))
        return unique_paa
    return []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/suggest', methods=['GET'])
def suggest():
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    suggestions = get_google_suggest(query)
    
    results = []
    for suggestion in suggestions:
        long_tails = get_long_tail_keywords(suggestion)
        paa = get_people_also_ask(suggestion)
        results.append({
            "suggestion": suggestion,
            "long_tails": long_tails,
            "paa": paa
        })

    return jsonify({'query': query, 'results': results})

@app.route('/download', methods=['POST'])
def download_file():
    if request.method == 'POST':
        data = request.json
        suggestion = data.get('suggestion')
        long_tails = data.get('long_tails', [])
        paa = data.get('paa', [])

        # Membuat konten file
        content = f"Keyword: {suggestion}\n\n"
        content += "Long-Tail Keywords:\n"
        content += "\n".join(f"- {lt}" for lt in long_tails)
        content += "\n\nPeople Also Ask:\n"
        content += "\n".join(f"- {p}" for p in paa)
        
# Menyimpan file di memory sementara
        filename = f"{suggestion}.txt"
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(content)

        # Mengirimkan file kepada pengguna
        return send_file(filename, as_attachment=True)

    
@app.route('/batch-download', methods=['POST'])
def batch_download():
    # Pastikan hanya menerima POST
    if request.method == 'POST':
        data = request.json
        results = data.get('results', [])

        # Membuat file ZIP
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for result in results:
                suggestion = result.get('suggestion', 'Unknown')
                long_tails = result.get('long_tails', [])
                paa = result.get('paa', [])

                # Konten file per keyword
                content = f"Keyword: {suggestion}\n\n"
                content += "Long-Tail Keywords:\n"
                content += "\n".join(f"- {lt}" for lt in long_tails)
                content += "\n\nPeople Also Ask:\n"
                content += "\n".join(f"- {p}" for p in paa)
                content += "\n\n"

                # Tambahkan file ke ZIP
                zf.writestr(f"{suggestion}.txt", content)

        # Kembalikan file ZIP
        memory_file.seek(0)
        return Response(
            memory_file,
            mimetype='application/zip',
            headers={"Content-Disposition": "attachment;filename=batch_results.zip"}
        )
    return jsonify({"error": "Invalid method"}), 405
    
@app.route('/download-all', methods=['POST'])
def download_all():
    if request.method == 'POST':
        data = request.json
        results = data.get('results', [])

        # Membuat konten file
        content = ""
        for result in results:
            suggestion = result.get('suggestion', 'Unknown')
            long_tails = result.get('long_tails', [])
            paa = result.get('paa', [])

            content += f"Keyword: {suggestion}\n\n"
            content += "Long-Tail Keywords:\n"
            content += "\n".join(f"- {lt}" for lt in long_tails)
            content += "\n\nPeople Also Ask:\n"
            content += "\n".join(f"- {p}" for p in paa)
            content += "\n\n" + "="*50 + "\n\n"

        # Mengirimkan file sebagai respons
        return Response(
            content,
            mimetype="text/plain",
            headers={"Content-Disposition": "attachment;filename=all_results.txt"}
        )
    return jsonify({"error": "Invalid method"}), 405
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
