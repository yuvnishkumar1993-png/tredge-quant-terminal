import requests

class DhanAPIClient:
    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.base_url = "https://api.dhan.co/v2"

    def _get_headers(self) -> dict:
        return {
            "access-token": self.access_token,
            "client-id": self.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def fetch_option_chain(self, scrip_id: int, segment: str, expiry_date: str) -> dict:
        url = f"{self.base_url}/optionchain"
        payload = {
            "underlyingScrip": scrip_id,
            "underlyingSegment": segment,
            "expiry": expiry_date
        }
        try:
            response = requests.post(url, json=payload, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                return {"status": "success", "data": response.json()}
            else:
                return {"status": "error", "message": f"API Error {response.status_code}: {response.text}"}
        except Exception as e:
            return {"status": "error", "message": f"Connection Failed: {str(e)}"}
