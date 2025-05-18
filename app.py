from flask import Flask, request, jsonify
import requests
import time
import bs4

from x_client_transaction import ClientTransaction
from x_client_transaction.utils import generate_headers, handle_x_migration, get_ondemand_file_url

app = Flask(__name__)

# RAM cache için global değişkenler
cached_home_html = None
cached_ondemand_soup = None
last_cache_time = 0
CACHE_TTL_SECONDS = 120  # 2 dakika boyunca cache geçerli


def get_cached_transaction_environment():
    global cached_home_html, cached_ondemand_soup, last_cache_time

    now = time.time()
    if cached_home_html and cached_ondemand_soup and (now - last_cache_time < CACHE_TTL_SECONDS):
        # Cache geçerli, doğrudan döndür
        return cached_home_html, cached_ondemand_soup

    # Cache geçerli değil, verileri yeniden al
    session = requests.Session()
    session.headers = generate_headers()

    # x.com/home sayfası alınıyor, gerekirse x.com/x/migrate yönlendirmesi de takip ediliyor
    home_html = handle_x_migration(session=session)

    # ondemand.js dosyasının URL'si çıkarılıyor
    ondemand_url = get_ondemand_file_url(response=home_html)
    if not ondemand_url:
        raise Exception("ondemand.js dosyası bulunamadı.")

    # ondemand içeriği çekiliyor ve parse ediliyor
    ondemand_file = session.get(ondemand_url)
    ondemand_soup = bs4.BeautifulSoup(ondemand_file.content, "html.parser")

    # Cache güncelleniyor
    cached_home_html = home_html
    cached_ondemand_soup = ondemand_soup
    last_cache_time = now

    return cached_home_html, cached_ondemand_soup


@app.route("/generate_id", methods=["POST"])
def generate_id():
    try:
        data = request.get_json()
        if not data or 'method' not in data or 'path' not in data:
            return jsonify({"error": "Lütfen 'method' ve 'path' parametrelerini gönderin."}), 400

        method = data["method"]
        path = data["path"]

        # Cache üzerinden veya güncelleyerek HTML + JS içeriğini al
        home_html, ondemand_soup = get_cached_transaction_environment()

        # Transaction ID üretimi
        ct = ClientTransaction(home_page_response=home_html,
                               ondemand_file_response=ondemand_soup)
        transaction_id = ct.generate_transaction_id(method=method, path=path)

        return jsonify({"transaction_id": transaction_id})

    except Exception as e:
        return jsonify({"error": f"Hata oluştu: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
