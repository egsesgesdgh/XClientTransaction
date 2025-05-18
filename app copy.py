import requests
import bs4
from flask import Flask, request, jsonify
# XClientTransaction kütüphanesinden gerekli sınıf ve fonksiyonları içe aktarıyoruz
from x_client_transaction import ClientTransaction
from x_client_transaction.utils import generate_headers, handle_x_migration, get_ondemand_file_url

app = Flask(__name__)


@app.route('/generate_id', methods=['POST'])
def generate_id():
    # İstekten JSON verisini al
    data = request.get_json()
    if not data or 'method' not in data or 'path' not in data:
        return jsonify({"error": "Lütfen 'method' ve 'path' değerlerini JSON formatında gönderin."}), 400

    method = data['method']
    path = data['path']

    # X ana sayfasını çekmek için bir oturum oluştur ve gerekli header'ları ekle
    session = requests.Session()
    session.headers = generate_headers()
    home_page_response = handle_x_migration(
        session=session)  # x.com ana sayfa HTML'ini al

    # Ana sayfadan ondemand.s dosyasının URL'ini bul ve içeriğini al
    ondemand_url = get_ondemand_file_url(response=home_page_response)
    if not ondemand_url:
        return jsonify({"error": "ondemand.s dosya URL'i ana sayfadan alınamadı."}), 500
    ondemand_file = session.get(ondemand_url)
    ondemand_file_response = bs4.BeautifulSoup(
        ondemand_file.content, 'html.parser')

    # Transaction ID üretimi
    ct = ClientTransaction(home_page_response=home_page_response,
                           ondemand_file_response=ondemand_file_response)
    transaction_id = ct.generate_transaction_id(method=method, path=path)

    return jsonify({"transaction_id": transaction_id})
