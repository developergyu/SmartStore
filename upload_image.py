import requests

url = "https://api.commerce.naver.com/external/v1/product-images/upload"

# 이미지 URL을 전송하기 위해 'files'를 사용해 multipart로 보내기
files = {
    'imageFiles': ('car_neck_pillow_07.jpg', requests.get("https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_07.jpg").content, 'image/jpeg')
}

headers = {
    'Accept': 'application/json;charset=UTF-8',
    'Authorization': 'Bearer 2zs80sU8F07r9bO4XkZ38'
}

# POST 요청 보내기
response = requests.post(url, headers=headers, files=files)

# 결과 출력
print(response.text)
