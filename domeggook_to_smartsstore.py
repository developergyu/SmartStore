import http.client
import bcrypt
import pybase64
import urllib.parse
import json
import time
import os
import requests
import mimetypes
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, Union, Optional, List
from PIL import Image


@dataclass
class Product:
    title: str                  #제목
    price: str                  #가격
    inventory: str              #재고
    domeggook_thumb_url: str    #도매꾹 썸네일 이미지
    representativeImage: str    #대표이미지
    optionalImages: str         #추가이미지
    secondExtraFee: int     #제주추가배송비
    thirdExtraFee: int      #도서산간추가배송비
    originAreaCode: str     #원산지정보
    manufacturerName: str   #제조사
    selectOpt: Dict[str, Union[str, List[str]]]              #옵션
    deliveryFee: Dict[str, Union[str, int]]  #배송관련
    detailContent: str                             #상세페이지 이미지
    categories: str                             #카탈로그
    smartstore_CategoryId: int                  #smartstore 카탈로그
    fromOversea: bool                            #해외배송여부
    

# 필요한 필드 추가

# 설정 값 (clientId, clientSecret 등)
client_id = "5XJumV8jd3c2dbG9oF98X1"
client_secret = "$2a$04$Oi1tLN44O4mhRHUoaJzrVO"
# domeggook_product_no = "42548729"
# smartstore_title = "족저근막염 양말 TXG Plantar Socks 흰색"
# smartstore_CategoryId = None

import os

def check_and_append_product_no(domeggook_product_no):
    base_dir = os.path.join(os.path.dirname(__file__), "SmartStore_image")
    os.makedirs(base_dir, exist_ok=True)
    
    file_path = os.path.join(base_dir, "product.txt")
    
    # 파일이 없으면 생성
    if not os.path.exists(file_path):
        open(file_path, 'a', encoding='utf-8').close()
    
    # 이미 등록된 상품인지 확인
    with open(file_path, 'r', encoding='utf-8') as f:
        registered_nos = {line.strip() for line in f}

    if str(domeggook_product_no) in registered_nos:
        print("이미 등록한 상품")
        return True
    return False


def domeggook_search_product(no,title) -> Product:

    # API URL
    url = "https://domeggook.com/ssl/api"

    params = {
        'ver': '4.5',
        'mode': 'getItemView',
        'aid': '5770d1b96006f2b3c91631b6e8d4cadc',
        'om': 'xml',
        'no': f'{no}'  # 조회할 상품 번호
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        root = ET.fromstring(response.text)
        license_free = root.findtext('.//desc//license//usable')
        supplyUnit = root.findtext('.//qty//supplyUnit')
        if not supplyUnit:
            supplyUnit = root.findtext('.//qty//domeUnit')
    else:
        print("HTTP 요청 실패:", response.status_code)
    
    #이미지 사용 가능할때만 + 구매 단위 1 있을때
    if license_free == "true" and supplyUnit == "1":

        # items = root.findall('./list/item')
        # if not items:
        #     print("상품이 없습니다.")
        # else:
        #     for item in items:
        title = title#root.findtext('.//title')                              #상풍명
        print(title, no)
        price = root.findtext('.//price//supply')                                 #도매매 금액
        if not price:
            price = root.findtext('.//price//dome')                                 #도매꾹 금액
        inventory =  root.findtext('.//qty/inventory')                     #재고
        domeggook_thumb_url = root.findtext('.//thumb/original')             #썸네일url
        representativeImage = None
        optionalImages = None                                               #옵션이미지url
        deliveryFee = parse_delivery_type_and_fee(root)                      #배송관련
        # baseFee = root.findtext('.//deli//supply//fee')                              #기본배송비
        secondExtraFee = root.findtext('.//jeju')                      #제주추가배송비
        thirdExtraFee = root.findtext('.//islands')                    #도서산간 추가 배송비
        originAreaCode = map_origin_code(root.findtext('.//country'))#원산지
        manufacturerName = root.findtext('.//detail//manufacturer') #제조사
        selectOpt = map_option_code(root.findtext('.//selectOpt'))     #옵션
        name_list = [elem.text for elem in root.findall('.//category//name')]
        categories = get_categories_no(name_list)
        detailContent = root.findtext(".//contents//item").strip()                  #상세페이지
        fromOversea = root.findtext('.//deli//fromOversea') #해외배송 여부
        # 추가할 문구 HTML로 작성
        additional_content = """
            <div style="text-align: center; font-size: 16px;">
                <br>제조사/유통사/3PL 등에서 출고될 수 있는<br>
                위탁 상품을 취급하고 있습니다.<br>
                개인정보를 제3자에게 제공할 수 있음을<br>
                사전에 고지 드립니다.<br>
                (해당 개인정보는<br>
                주문 및 배송용으로만 사용되며,<br>
                물건을 구매 시<br>
                이에 동의한 것으로 간주합니다)
            </div>
        """
        detailContent += additional_content

        return Product(
            title=title,
            price=price,
            inventory = inventory,
            domeggook_thumb_url = domeggook_thumb_url,
            representativeImage = representativeImage,
            optionalImages = optionalImages,
            deliveryFee = deliveryFee,
            # baseFee = baseFee,
            secondExtraFee = secondExtraFee,
            thirdExtraFee = thirdExtraFee,
            originAreaCode = originAreaCode,
            manufacturerName = manufacturerName,
            selectOpt = selectOpt,
            detailContent = detailContent,
            categories = categories,
            smartstore_CategoryId = None,
            fromOversea = fromOversea
        )
    else:
        print("조건 안맞는 상품")
        # exit()      
    
def generate_client_secret_sign(client_id, client_secret):
    """
    주어진 client_id와 client_secret을 이용하여 client_secret_sign을 생성합니다.
    """
    # 현재 Unix 시간 (밀리초 단위)
    timestamp = int(time.time() * 1000)

    # client_id와 timestamp로 password 생성
    password = f"{client_id}_{timestamp}"

    # bcrypt 해싱
    hashed = bcrypt.hashpw(password.encode('utf-8'), client_secret.encode('utf-8'))

    # base64 인코딩
    client_secret_sign = pybase64.standard_b64encode(hashed).decode('utf-8')
    
    return timestamp, client_secret_sign

def get_access_token(client_id, client_secret):
    """
    API에 요청을 보내어 access_token을 얻어옵니다.
    """
    timestamp, client_secret_sign = generate_client_secret_sign(client_id, client_secret)

    # 토큰 요청 파라미터 설정
    params = {
        'client_id': client_id,
        'timestamp': str(timestamp),
        'grant_type': 'client_credentials',
        'client_secret_sign': client_secret_sign,
        'type': 'SELF'
    }

    payload = urllib.parse.urlencode(params)

    # 요청 헤더 설정
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }

    # HTTP 요청 보내기
    conn = http.client.HTTPSConnection("api.commerce.naver.com")
    conn.request("POST", "/external/v1/oauth2/token", payload, headers)
    res = conn.getresponse()
    
    # 응답에서 토큰 추출
    data = res.read()
    token = json.loads(data.decode("utf-8"))["access_token"]

    return token

def parse_delivery_type_and_fee(root):

    #무료배송(도매꾹에서만 파는 경우 deli/pay, 도매매에도 있는 경우 deli/supply/pay)
    if root.findtext('.//deli//pay') == "무료배송" or root.findtext('.//deli//supply//pay') == "무료배송":
        delivery_fee_type = "FREE"
        base_fee = 3000
        repeatQuantity = 0

    else:
        delivery_type = root.findtext('.//deli//supply//type')
        delivery_fee_type = ""
        base_fee = 3000
        repeatQuantity = 0

        if delivery_type == "수량별비례":
            delivery_fee_type = "UNIT_QUANTITY_PAID"
            tbl_value = root.findtext('.//deli//supply//tbl')
            if tbl_value:
                # 예: "40+3000|40+3000" → 첫 번째 값만 사용
                first_pair = tbl_value.split('|')[0]
                try:
                    repeatQuantity, base_fee = map(int, first_pair.split('+'))
                except ValueError:
                    print("tbl parsing error:", first_pair)
        elif delivery_type == "고정배송비":
            delivery_fee_type = "PAID"
            fee_value = root.findtext('.//deli//supply//fee')
            try:
                base_fee = int(fee_value) if fee_value else 3000
            except ValueError:
                print("fee parsing error:", fee_value)

    return {
        "deliveryFeeType": delivery_fee_type,
        "baseFee": base_fee,
        "repeatQuantity": repeatQuantity
    }

def map_origin_code(text: str) -> str:
    origin_map = {
        "국산": "00",
        "원양산": "01",
#        "수입산": "02",
        "수입산" : "03",    #수입산도 그냥 03으로 표시
        "기타-상세 설명에 표시": "03",
        "기타-직접 입력": "04",
        "원산지 표기 의무 대상 아님": "05"
    }

    for key in origin_map:
        if key in text:
            return origin_map[key]
    
    return "03"  # 매칭되지 않으면 기본값

def map_option_code(text: str) -> str:

    if not text:
        group_name = "옵션없음"
        name = "옵션없음"
        qty_values = None

        result = {
            "groupName": group_name,
            "name": name,
            "qty": qty_values
        }
    else:
        parsed = json.loads(text)
        group_name = parsed['set'][0]['name']
        data = parsed['data']

        # qty가 0이 아닌 것만 필터링
        option_values = []
        qty_values = []
        for item in data.values():
            if item['qty'] != "0":
                option_values.append(item['name'])
                qty_values.append(item['qty'])

        result = {
            "groupName": group_name,
            "name": [opt[:25] for opt in option_values],
            "qty": qty_values
        }

    return json.dumps(result, ensure_ascii=False)

def fetch_product_data(token):
    """
    access_token을 사용하여 상품 데이터를 요청합니다.
    """
    # 상품 조회 요청 파라미터 설정
    payload = json.dumps({
        "searchKeywordType": "11816257457"
    })

    # 요청 헤더 설정
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json;charset=UTF-8',
        'Authorization': f'Bearer {token}'
    }

    # HTTP 요청 보내기
    conn = http.client.HTTPSConnection("api.commerce.naver.com")
    conn.request("POST", "/external/v1/products/search", payload, headers)
    res = conn.getresponse()

    # 응답 데이터 출력
    data = res.read()
    print(data.decode("utf-8"))
    conn.close()

def categories_data(token):

    payload = ''
    # 요청 헤더 설정
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json;charset=UTF-8',
        'Authorization': f'Bearer {token}'
    }

    # HTTP 요청 보내기
    conn = http.client.HTTPSConnection("api.commerce.naver.com")
    conn.request("GET", "/external/v1/categories", payload, headers)
    res = conn.getresponse()
    data = res.read()
    json_data = json.loads(data)
    return json_data

def registry_product(token, product: Product, no):

    conn = http.client.HTTPSConnection("api.commerce.naver.com")
    #옵션이 없을때
    if json.loads(product.selectOpt)["groupName"] == "옵션없음":
        payload = json.dumps({
        "originProduct": {
            "statusType": "SALE",               #상품 판매 상태 코드(필수)
            "saleType": "NEW",                  #상품 판매 유형 코드
            "leafCategoryId": f'{product.smartstore_CategoryId}',       #리프 카테고리 ID
            "name": f'{product.title}',         #이름(필수)
            "detailContent": f'{product.detailContent}',
            "images": {                         #필수
            "representativeImage": {            #썸네일
                "url": f'{product.representativeImage}'
            },
            "optionalImages": [
                {
                "url": f'{product.representativeImage}'
                }
            ]
            },
            "salePrice": f'{(int(int(product.price) * 1.43) // 10) * 10}',
            "stockQuantity": f'{product.inventory}',      #재고
            "deliveryInfo": {
            "deliveryType": "DELIVERY",                     #필수
            "deliveryAttributeType": "NORMAL",              #필수
            "deliveryCompany": "CJGLS",                     #CJ
            "deliveryFee": {                #필수
                "deliveryFeeType": f'{product.deliveryFee["deliveryFeeType"]}',
                "baseFee": f'{product.deliveryFee["baseFee"]}',
                "repeatQuantity": f'{product.deliveryFee["repeatQuantity"]}',
                "deliveryFeePayType": "PREPAID",  #배송비 결제 방법
                "deliveryFeeByArea": {
                "deliveryAreaType": "AREA_3",
                "area2extraFee": f'{product.secondExtraFee}',
                "area3extraFee": f'{product.thirdExtraFee}'
                },
            },
            "claimDeliveryInfo": {                                                      #필수
                "returnDeliveryCompanyPriorityType": "PRIMARY",
                "returnDeliveryFee": f'{product.deliveryFee["baseFee"]}',                                   #반품 배송비(필수)
                "exchangeDeliveryFee": f'{int(product.deliveryFee["baseFee"]) * 2}',                        #교환 배송비(필수)
            },
            },
            "detailAttribute": {                    #원상품 상세 속성
            "naverShoppingSearchInfo": {
                "modelName": f'{product.title}',
                "manufacturerName": f'{product.manufacturerName}',
                "brandName": "히카소 마트 협력사"
            },
            "afterServiceInfo": {                         #A/S 정보(필수)
                "afterServiceTelephoneNumber": "010-7248-1242",  #A/S 전화번호(필수)
                "afterServiceGuideContent": "제품 이상시 네이버톡톡으로 문의 주시기 바랍니다."      #A/S 안내(필수)
            },
            "originAreaInfo": {                                                 #원산지 정보(필수)
                "originAreaCode": f'{product.originAreaCode}',                 #원산지 상세 지역 코드(필수) 00(국산), 01(원양산), 02(수입산), 03(기타-상세 설명에 표시), 04(기타-직접 입력), 05(원산지 표기 의무 대상 아님)
                #"originAreaCode" : "03",
                "importer": "협력사",
                "content": "중국"
            },
            "minorPurchasable": True,                       #미성년자 구매 가능 여부(필수)
            "productInfoProvidedNotice": {
                "productInfoProvidedNoticeType": "ETC",        #상품정보제공고시 상품군 유형(필수)
                "etc": {
                "returnCostReason": 0,
                "noRefundReason": 0,
                "qualityAssuranceStandard": 0,
                "compensationProcedure": 0,
                "troubleShootingContents": 0,
                "itemName": "상품상세참조",
                "modelName": "상품상세참조",
                "certificateDetails": "상품상세참조",
                "manufacturer": "상품상세참조",
                "afterServiceDirector": "상품상세참조",
                }
            },
            },
            "customerBenefit": {
            "immediateDiscountPolicy": {
                "discountMethod": {
                "value": 17,
                "unitType": "PERCENT"
                }
            },
            "reviewPointPolicy": {
                "textReviewPoint": 100,
                "photoVideoReviewPoint": 200
            },
            }
        },
        "smartstoreChannelProduct": {
            "naverShoppingRegistration": True,
            "channelProductDisplayStatusType": "ON"
        },
        })
    #옵션이 있는 경우
    else:
        payload = json.dumps({
        "originProduct": {
            "statusType": "SALE",               #상품 판매 상태 코드(필수)
            "saleType": "NEW",                  #상품 판매 유형 코드
            "leafCategoryId": f'{product.smartstore_CategoryId}',       #리프 카테고리 ID
            "name": f'{product.title}',         #이름(필수)
            "detailContent": f'{product.detailContent}',
            # "detailContent": "<!DOCTYPE html>\n<html lang=\"ko\">\n<head>\n  <meta charset=\"UTF-8\">\n  <style>\n    .product-images {\n      display: flex;\n      flex-direction: column;\n      align-items: center;\n    }\n    .product-images img {\n      max-width: 100%;\n      margin-bottom: 10px;\n    }\n    .notice {\n      text-align: center;\n      font-size: 22px;\n      margin-top: 20px;\n      line-height: 1.5;\n      white-space: pre-line;\n    }\n  </style>\n</head>\n<body>\n  <div class=\"product-images\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_01.jpg\" alt=\"목쿠션 이미지 01\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_02.jpg\" alt=\"목쿠션 이미지 02\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_03.jpg\" alt=\"목쿠션 이미지 03\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_04.jpg\" alt=\"목쿠션 이미지 04\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_05.jpg\" alt=\"목쿠션 이미지 05\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_06.jpg\" alt=\"목쿠션 이미지 06\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_07.jpg\" alt=\"목쿠션 이미지 07\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_08.jpg\" alt=\"목쿠션 이미지 08\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_09.jpg\" alt=\"목쿠션 이미지 09\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_10.jpg\" alt=\"목쿠션 이미지 10\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_11.jpg\" alt=\"목쿠션 이미지 11\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_12.jpg\" alt=\"목쿠션 이미지 12\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_13.jpg\" alt=\"목쿠션 이미지 13\">\n    <img src=\"https://wgfood.negagea.kr/주의사항/이염주의_작게.jpg\" alt=\"주의사항\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_14_00.jpg\" alt=\"목쿠션 이미지 14\">\n  </div>\n\n  <div class=\"notice\">\n    제조사/유통사/3PL 등에서 출고될 수 있는<br>\n    위탁 상품을 취급하고 있습니다.<br>\n    개인정보를 제3자에게 제공할 수 있음을<br>\n    사전에 고지 드립니다.<br>\n    (해당 개인정보는<br>\n    주문 및 배송용으로만 사용되며,<br>\n    물건을 구매 시<br>\n    이에 동의한 것으로 간주합니다)<br>\n  </div>\n</body>\n</html>",
            "images": {                         #필수
            "representativeImage": {            #썸네일
                "url": f'{product.representativeImage}'
            },
            "optionalImages": [
                {
                "url": f'{product.representativeImage}'
                }
            ]
            },
            # "saleStartDate": "2024-07-29T15:51:28.071Z",   
            # "saleEndDate": "2024-07-29T15:51:28.071Z",
            "salePrice": f'{(int(int(product.price) * 1.43) // 10) * 10}',
            "stockQuantity": f'{product.inventory}',      #재고
            "deliveryInfo": {
            "deliveryType": "DELIVERY",                     #필수
            "deliveryAttributeType": "NORMAL",              #필수
            "deliveryCompany": "CJGLS",                     #CJ
            # "outboundLocationId": "string",
            # "deliveryBundleGroupUsable": False,
            # "deliveryBundleGroupId": 0,
            # "quickServiceAreas": [
            #     "SEOUL"
            # ],
            # "visitAddressId": 0,
            "deliveryFee": {                #필수
                "deliveryFeeType": f'{product.deliveryFee["deliveryFeeType"]}',
                "baseFee": f'{product.deliveryFee["baseFee"]}',
                # "freeConditionalAmount": 0,
                "repeatQuantity": f'{product.deliveryFee["repeatQuantity"]}',
                # "secondBaseQuantity": 0,
                # "secondExtraFee": 0,
                # "thirdBaseQuantity": 0,
                # "thirdExtraFee": 0',
                "deliveryFeePayType": "PREPAID",  #배송비 결제 방법
                "deliveryFeeByArea": {
                "deliveryAreaType": "AREA_3",
                "area2extraFee": f'{product.secondExtraFee}',
                "area3extraFee": f'{product.thirdExtraFee}'
                },
                # "differentialFeeByArea": "string"
            },
            "claimDeliveryInfo": {                                                      #필수
                "returnDeliveryCompanyPriorityType": "PRIMARY",
                "returnDeliveryFee": f'{product.deliveryFee["baseFee"]}',                          #반품 배송비(필수)
                "exchangeDeliveryFee": f'{int(product.deliveryFee["baseFee"]) * 2}'                        #교환 배송비(필수)
                # "shippingAddressId": 0,
                # "returnAddressId": 0,
                # "freeReturnInsuranceYn": True
            },
            # "installation": False,
            # "installationFee": False,
            # "expectedDeliveryPeriodType": "ETC",
            # "expectedDeliveryPeriodDirectInput": "string",
            # "todayStockQuantity": 0,
            # "customProductAfterOrderYn": False,
            # "hopeDeliveryGroupId": 0,
            # "businessCustomsClearanceSaleYn": False
            },
            # "productLogistics": [
            # {
            #     "logisticsCompanyId": "string"
            # }
            # ],
            "detailAttribute": {                    #원상품 상세 속성
            "naverShoppingSearchInfo": {
                # "modelId": 0,
                "modelName": f'{product.title}',
                "manufacturerName": f'{product.manufacturerName}',
                # "brandId": 0,
                "brandName": "히카소 마트 협력사"
            },
            # "manufactureDefineNo": "string",
            "afterServiceInfo": {                         #A/S 정보(필수)
                "afterServiceTelephoneNumber": "010-7248-1242",  #A/S 전화번호(필수)
                "afterServiceGuideContent": "제품 이상시 네이버톡톡으로 문의 주시기 바랍니다."      #A/S 안내(필수)
            },
            # "purchaseQuantityInfo": {                             #1인당 구매 수량
            #     "minPurchaseQuantity": 0,
            #     "maxPurchaseQuantityPerId": 0,
            #     "maxPurchaseQuantityPerOrder": 0
            # },
            "originAreaInfo": {                                                 #원산지 정보(필수)
                "originAreaCode": f'{product.originAreaCode}',                 #원산지 상세 지역 코드(필수) 00(국산), 01(원양산), 02(수입산), 03(기타-상세 설명에 표시), 04(기타-직접 입력), 05(원산지 표기 의무 대상 아님)
                #"originAreaCode" : "03",
                "importer": "협력사",
                "content": "중국"
                # "plural": True
            },
            # "sellerCodeInfo": {
            #     "sellerManagementCode": "string",
            #     "sellerBarcode": "string",
            #     "sellerCustomCode1": "string",
            #     "sellerCustomCode2": "string"
            # },
            "optionInfo": {
                "simpleOptionSortType": "CREATE",
                "optionSimple": [
                {
                    # "id": 0,
                    "groupName": f'{json.loads(product.selectOpt)["groupName"]}',           #옵션명
                    "name": name,                                                           #옵션값
                    # "usable": True
                }
                    for name in json.loads(product.selectOpt)["name"]
                ],
                # "optionCustom": [
                # {
                #     "id": 0,
                #     "groupName": "string",
                #     "name": "string",
                #     "usable": True
                # }
                # ],
            #     "optionCombinationSortType": "CREATE",
            #     "optionCombinationGroupNames": {
            #     "optionGroupName1": "string",
            #     "optionGroupName2": "string",
            #     "optionGroupName3": "string",
            #     "optionGroupName4": "string"
            #     },
            #     "optionCombinations": [
            #     {
            #         "id": 0,
            #         "stockQuantity": 0,
            #         "price": 0,
            #         "usable": True,
            #         "optionName1": "string",
            #         "optionName2": "string",
            #         "optionName3": "string",
            #         "optionName4": "string",
            #         "sellerManagerCode": "string"
            #     }
            #     ],
            #     "standardOptionGroups": [
            #     {
            #         "groupName": "string",
            #         "standardOptionAttributes": [
            #         {
            #             "attributeId": 0,
            #             "attributeValueId": 0,
            #             "attributeValueName": "string",
            #             "imageUrls": [
            #             "string"
            #             ]
            #         }
            #         ]
            #     }
            #     ],
            #     "optionStandards": [
            #     {
            #         "id": 0,
            #         "stockQuantity": 0,
            #         "usable": True,
            #         "optionName1": "string",
            #         "optionName2": "string",
            #         "sellerManagerCode": "string"
            #     }
            #     ],
            #     "useStockManagement": True,
            #     "optionDeliveryAttributes": [
            #     "string"
            #     ]
            },
            # "supplementProductInfo": {
            #     "sortType": "CREATE",
            #     "supplementProducts": [
            #     {
            #         "id": 0,
            #         "groupName": "string",
            #         "name": "string",
            #         "price": 0,
            #         "stockQuantity": 0,
            #         "sellerManagementCode": "string",
            #         "usable": True
            #     }
            #     ]
            # },
            # "purchaseReviewInfo": {
            #     "purchaseReviewExposure": True,
            #     "reviewUnExposeReason": "string"
            # },
            # "isbnInfo": {
            #     "isbn13": "string",
            #     "issn": "string",
            #     "independentPublicationYn": True
            # },
            # "bookInfo": {
            #     "publishDay": "string",
            #     "publisher": {
            #     "code": "string",
            #     "text": "string"
            #     },
            #     "authors": [
            #     {
            #         "code": "string",
            #         "text": "string"
            #     }
            #     ],
            #     "illustrators": [
            #     {
            #         "code": "string",
            #         "text": "string"
            #     }
            #     ],
            #     "translators": [
            #     {
            #         "code": "string",
            #         "text": "string"
            #     }
            #     ]
            # },
            # "eventPhraseCont": "string",
            # "manufactureDate": "2024-07-29",
            # "releaseDate": "2024-07-29",
            # "validDate": "2024-07-29",
            # "taxType": "TAX",
            # "productCertificationInfos": [
            #     {
            #     "certificationInfoId": 0,
            #     "certificationKindType": "KC_CERTIFICATION",
            #     "name": "string",
            #     "certificationNumber": "string",
            #     "certificationMark": True,
            #     "companyName": "string",
            #     "certificationDate": "2024-07-29"
            #     }
            # ],
            # "certificationTargetExcludeContent": {
            #     "childCertifiedProductExclusionYn": True,
            #     "kcExemptionType": "OVERSEAS",
            #     "kcCertifiedProductExclusionYn": "FALSE",
            #     "greenCertifiedProductExclusionYn": True
            # },
            # "sellerCommentContent": "string",
            # "sellerCommentUsable": True,
            "minorPurchasable": True,                       #미성년자 구매 가능 여부(필수)
            # "ecoupon": {
            #     "periodType": "FIXED",
            #     "validStartDate": "2024-07-29",
            #     "validEndDate": "2024-07-29",
            #     "periodDays": 0,
            #     "publicInformationContents": "string",          #E쿠폰 발행처 내용(필수)
            #     "contactInformationContents": "string",         #E쿠폰 연락처 내용(필수)
            #     "usePlaceType": "PLACE",                        #E쿠폰 사용 장소 구분 코드(필수)
            #     "usePlaceContents": "string",                   #사용 장소 내용(필수)
            #     "restrictCart": True,
            #     "siteName": "string"
            # },
            "productInfoProvidedNotice": {
                "productInfoProvidedNoticeType": "ETC",        #상품정보제공고시 상품군 유형(필수)
                # "wear": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "material": "string",
                # "color": "string",
                # "size": "string",
                # "manufacturer": "string",
                # "caution": "string",
                # "packDate": "string",
                # "packDateText": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "shoes": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "material": "string",
                # "color": "string",
                # "size": "string",
                # "height": "string",
                # "manufacturer": "string",
                # "caution": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "bag": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "type": "string",
                # "material": "string",
                # "color": "string",
                # "size": "string",
                # "manufacturer": "string",
                # "caution": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "fashionItems": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "type": "string",
                # "material": "string",
                # "size": "string",
                # "manufacturer": "string",
                # "caution": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "sleepingGear": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "material": "string",
                # "color": "string",
                # "size": "string",
                # "components": "string",
                # "manufacturer": "string",
                # "caution": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "furniture": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "certificationType": "string",
                # "color": "string",
                # "components": "string",
                # "material": "string",
                # "manufacturer": "string",
                # "importer": "string",
                # "producer": "string",
                # "size": "string",
                # "installedCharge": "string",
                # "warrantyPolicy": "string",
                # "refurb": "string",
                # "afterServiceDirector": "string"
                # },
                # "imageAppliances": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "certificationType": "string",
                # "ratedVoltage": "string",
                # "powerConsumption": "string",
                # "energyEfficiencyRating": "string",
                # "releaseDate": "string",
                # "releaseDateText": "string",
                # "manufacturer": "string",
                # "size": "string",
                # "additionalCost": "string",
                # "displaySpecification": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "homeAppliances": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "certificationType": "string",
                # "ratedVoltage": "string",
                # "powerConsumption": "string",
                # "energyEfficiencyRating": "string",
                # "releaseDate": "string",
                # "releaseDateText": "string",
                # "manufacturer": "string",
                # "size": "string",
                # "additionalCost": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "seasonAppliances": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "certificationType": "string",
                # "ratedVoltage": "string",
                # "powerConsumption": "string",
                # "energyEfficiencyRating": "string",
                # "releaseDate": {
                #     "year": 0,
                #     "month": "JANUARY",
                #     "monthValue": 0,
                #     "leapYear": True
                # },
                # "releaseDateText": "string",
                # "manufacturer": "string",
                # "size": "string",
                # "area": "string",
                # "installedCharge": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "officeAppliances": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "certificationType": "string",
                # "ratedVoltage": "string",
                # "powerConsumption": "string",
                # "energyEfficiencyRating": "string",
                # "releaseDate": {
                #     "year": 0,
                #     "month": "JANUARY",
                #     "monthValue": 0,
                #     "leapYear": True
                # },
                # "releaseDateText": "string",
                # "manufacturer": "string",
                # "size": "string",
                # "weight": "string",
                # "specification": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "opticsAppliances": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "certificationType": "string",
                # "releaseDate": "string",
                # "releaseDateText": "string",
                # "manufacturer": "string",
                # "size": "string",
                # "weight": "string",
                # "specification": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "microElectronics": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "certificationType": "string",
                # "ratedVoltage": "string",
                # "powerConsumption": "string",
                # "releaseDate": "string",
                # "releaseDateText": "string",
                # "manufacturer": "string",
                # "size": "string",
                # "weight": "string",
                # "specification": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "navigation": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "certificationType": "string",
                # "ratedVoltage": "string",
                # "powerConsumption": "string",
                # "releaseDate": "string",
                # "releaseDateText": "string",
                # "manufacturer": "string",
                # "size": "string",
                # "weight": "string",
                # "specification": "string",
                # "updateCost": "string",
                # "freeCostPeriod": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "carArticles": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "releaseDate": "string",
                # "releaseDateText": "string",
                # "certificationType": "string",
                # "caution": "string",
                # "manufacturer": "string",
                # "size": "string",
                # "applyModel": "string",
                # "warrantyPolicy": "string",
                # "roadWorthyCertification": "string",
                # "afterServiceDirector": "string"
                # },
                # "medicalAppliances": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "licenceNo": "string",
                # "advertisingCertificationType": "string",
                # "ratedVoltage": "string",
                # "powerConsumption": "string",
                # "releaseDate": "string",
                # "releaseDateText": "string",
                # "manufacturer": "string",
                # "purpose": "string",
                # "usage": "string",
                # "caution": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "kitchenUtensils": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "material": "string",
                # "component": "string",
                # "size": "string",
                # "releaseDate": "string",
                # "releaseDateText": "string",
                # "manufacturer": "string",
                # "producer": "string",
                # "importDeclaration": True,
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "cosmetic": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "capacity": "string",
                # "specification": "string",
                # "expirationDate": "string",
                # "expirationDateText": "string",
                # "usage": "string",
                # "manufacturer": "string",
                # "producer": "string",
                # "distributor": "string",
                # "customizedDistributor": "string",
                # "mainIngredient": "string",
                # "certificationType": "string",
                # "caution": "string",
                # "warrantyPolicy": "string",
                # "customerServicePhoneNumber": "string"
                # },
                # "jewellery": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "material": "string",
                # "purity": "string",
                # "bandMaterial": "string",
                # "weight": "string",
                # "manufacturer": "string",
                # "producer": "string",
                # "size": "string",
                # "caution": "string",
                # "specification": "string",
                # "provideWarranty": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "food": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "foodItem": "string",
                # "weight": "string",
                # "amount": "string",
                # "size": "string",
                # "packDate": "2024-07-29",
                # "packDateText": "string",
                # "consumptionDate": "2024-07-29",
                # "consumptionDateText": "string",
                # "producer": "string",
                # "relevantLawContent": "string",
                # "productComposition": "string",
                # "keep": "string",
                # "adCaution": "string",
                # "customerServicePhoneNumber": "string"
                # },
                # "generalFood": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "productName": "string",
                # "foodType": "string",
                # "producer": "string",
                # "location": "string",
                # "packDate": "2024-07-29",
                # "packDateText": "string",
                # "consumptionDate": "2024-07-29",
                # "consumptionDateText": "string",
                # "weight": "string",
                # "amount": "string",
                # "ingredients": "string",
                # "nutritionFacts": "string",
                # "geneticallyModified": True,
                # "consumerSafetyCaution": "string",
                # "importDeclarationCheck": True,
                # "customerServicePhoneNumber": "string"
                # },
                # "dietFood": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "productName": "string",
                # "producer": "string",
                # "location": "string",
                # "consumptionDate": "2024-07-29",
                # "consumptionDateText": "string",
                # "storageMethod": "string",
                # "weight": "string",
                # "amount": "string",
                # "ingredients": "string",
                # "nutritionFacts": "string",
                # "specification": "string",
                # "cautionAndSideEffect": "string",
                # "nonMedicinalUsesMessage": "string",
                # "geneticallyModified": True,
                # "importDeclarationCheck": True,
                # "consumerSafetyCaution": "string",
                # "customerServicePhoneNumber": "string"
                # },
                # "kids": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "certificationType": "string",
                # "size": "string",
                # "weight": "string",
                # "color": "string",
                # "material": "string",
                # "recommendedAge": "string",
                # "releaseDate": "string",
                # "releaseDateText": "string",
                # "manufacturer": "string",
                # "caution": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string",
                # "numberLimit": "string"
                # },
                # "musicalInstrument": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "size": "string",
                # "color": "string",
                # "material": "string",
                # "components": "string",
                # "releaseDate": "string",
                # "releaseDateText": "string",
                # "manufacturer": "string",
                # "detailContent": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "sportsEquipment": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "certificationType": "string",
                # "size": "string",
                # "weight": "string",
                # "color": "string",
                # "material": "string",
                # "components": "string",
                # "releaseDate": {
                #     "year": 0,
                #     "month": "JANUARY",
                #     "monthValue": 0,
                #     "leapYear": True
                # },
                # "releaseDateText": "string",
                # "manufacturer": "string",
                # "detailContent": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                # "books": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "title": "string",
                # "author": "string",
                # "publisher": "string",
                # "size": "string",
                # "pages": "string",
                # "components": "string",
                # "publishDate": "2024-07-29",
                # "publishDateText": "string",
                # "description": "string"
                # },
                # "rentalEtc": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "ownershipTransferCondition": "string",
                # "payingForLossOrDamage": "string",
                # "refundPolicyForCancel": "string",
                # "customerServicePhoneNumber": "string"
                # },
                # "rentalHa": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "ownershipTransferCondition": "string",
                # "payingForLossOrDamage": "string",
                # "refundPolicyForCancel": "string",
                # "customerServicePhoneNumber": "string",
                # "maintenance": "string",
                # "specification": "string"
                # },
                # "digitalContents": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "producer": "string",
                # "termsOfUse": "string",
                # "usePeriod": "string",
                # "medium": "string",
                # "requirement": "string",
                # "cancelationPolicy": "string",
                # "customerServicePhoneNumber": "string"
                # },
                # "giftCard": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "issuer": "string",
                # "periodStartDate": "2024-07-29",
                # "periodEndDate": "2024-07-29",
                # "periodDays": 0,
                # "termsOfUse": "string",
                # "useStorePlace": "string",
                # "useStoreAddressId": 0,
                # "useStoreUrl": "string",
                # "refundPolicy": "string",
                # "customerServicePhoneNumber": "string"
                # },
                # "mobileCoupon": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "issuer": "string",
                # "usableCondition": "string",
                # "usableStore": "string",
                # "cancelationPolicy": "string",
                # "customerServicePhoneNumber": "string"
                # },
                # "movieShow": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "sponsor": "string",
                # "actor": "string",
                # "rating": "string",
                # "showTime": "string",
                # "showPlace": "string",
                # "cancelationCondition": "string",
                # "cancelationPolicy": "string",
                # "customerServicePhoneNumber": "string"
                # },
                # "etcService": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "serviceProvider": "string",
                # "certificateDetails": "string",
                # "usableCondition": "string",
                # "cancelationStandard": "string",
                # "cancelationPolicy": "string",
                # "customerServicePhoneNumber": "string"
                # },
                # "biochemistry": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "productName": "string",
                # "dosageForm": "string",
                # "packDate": "string",
                # "packDateText": "string",
                # "expirationDate": "string",
                # "expirationDateText": "string",
                # "weight": "string",
                # "effect": "string",
                # "importer": "string",
                # "producer": "string",
                # "manufacturer": "string",
                # "childProtection": "string",
                # "chemicals": "string",
                # "caution": "string",
                # "safeCriterionNo": "string",
                # "customerServicePhoneNumber": "string"
                # },
                # "biocidal": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "productName": "string",
                # "weight": "string",
                # "effect": "string",
                # "rangeOfUse": "string",
                # "importer": "string",
                # "producer": "string",
                # "manufacturer": "string",
                # "childProtection": "string",
                # "harmfulChemicalSubstance": "string",
                # "maleficence": "string",
                # "caution": "string",
                # "approvalNumber": "string",
                # "customerServicePhoneNumber": "string",
                # "expirationDate": "2024-07-29",
                # "expirationDateText": "string"
                # },
                # "cellPhone": {
                # "returnCostReason": "string",
                # "noRefundReason": "string",
                # "qualityAssuranceStandard": "string",
                # "compensationProcedure": "string",
                # "troubleShootingContents": "string",
                # "itemName": "string",
                # "modelName": "string",
                # "certificationType": "string",
                # "releaseDate": "string",
                # "releaseDateText": "string",
                # "manufacturer": "string",
                # "importer": "string",
                # "producer": "string",
                # "size": "string",
                # "weight": "string",
                # "telecomType": "string",
                # "joinProcess": "string",
                # "extraBurden": "string",
                # "specification": "string",
                # "warrantyPolicy": "string",
                # "afterServiceDirector": "string"
                # },
                "etc": {
                "returnCostReason": 0,
                "noRefundReason": 0,
                "qualityAssuranceStandard": 0,
                "compensationProcedure": 0,
                "troubleShootingContents": 0,
                "itemName": "상품상세참조",
                "modelName": "상품상세참조",
                "certificateDetails": "상품상세참조",
                "manufacturer": "상품상세참조",
                "afterServiceDirector": "상품상세참조",
                # "customerServicePhoneNumber": "string"
                }
            },
            # "productAttributes": [
            #     {
            #     "attributeSeq": 0,
            #     "attributeValueSeq": 0,
            #     "attributeRealValue": "string",
            #     "attributeRealValueUnitCode": "string"
            #     }
            # ],
            # "cultureCostIncomeDeductionYn": True,
            # "customProductYn": True,
            # "itselfProductionProductYn": True,
            # "brandCertificationYn": True,
            # "seoInfo": {
            #     "pageTitle": "string",
            #     "metaDescription": "string",
            #     "sellerTags": [
            #     {
            #         "code": 0,
            #         "text": "string"
            #     }
            #     ]
            # },
            # "productSize": {
            #     "sizeTypeNo": 0,
            #     "sizeAttributes": [
            #     {
            #         "name": "string",
            #         "sizeValues": [
            #         {
            #             "sizeValueTypeNo": 0,
            #             "value": 0
            #         }
            #         ]
            #     }
            #     ],
            #     "models": [
            #     {
            #         "modelId": 0
            #     }
            #     ]
            # }
            },
            "customerBenefit": {
            "immediateDiscountPolicy": {
                "discountMethod": {
                "value": 17,
                "unitType": "PERCENT"
                # "startDate": "2024-07-29T15:51:28.071Z",
                # "endDate": "2024-07-29T15:51:28.071Z"
                }
            },
            # "purchasePointPolicy": {
            #     "value": 0,
            #     "unitType": "PERCENT",
            #     "startDate": "2024-07-29",
            #     "endDate": "2024-07-29"
            # },
            "reviewPointPolicy": {
                "textReviewPoint": 100,
                "photoVideoReviewPoint": 200
                # "afterUseTextReviewPoint": 0,
                # "afterUsePhotoVideoReviewPoint": 0,
                # "storeMemberReviewPoint": 0,
                # "startDate": "2024-07-29",
                # "endDate": "2024-07-29"
            },
            # "freeInterestPolicy": {
            #     "value": 0,
            #     "startDate": "2024-07-29",
            #     "endDate": "2024-07-29"
            # },
            # "giftPolicy": {
            #     "presentContent": "string"
            # },
            # "multiPurchaseDiscountPolicy": {
            #     "discountMethod": {
            #     "value": 0,
            #     "unitType": "PERCENT",
            #     "startDate": "2024-07-29",
            #     "endDate": "2024-07-29"
            #     },
            #     "orderValue": 0,
            #     "orderValueUnitType": "PERCENT"
            # },
            # "reservedDiscountPolicy": {
            #     "discountMethod": {
            #     "value": 0,
            #     "unitType": "PERCENT",
            #     "startDate": "2024-07-29T15:51:28.071Z",
            #     "endDate": "2024-07-29T15:51:28.071Z"
            #     }
            # }
            }
        },
        "smartstoreChannelProduct": {
            # "channelProductName": "string",
            # "bbsSeq": 0,
            # "storeKeepExclusiveProduct": True,
            "naverShoppingRegistration": True,
            "channelProductDisplayStatusType": "ON"
        },
        # "windowChannelProduct": {
        #     "channelProductName": "string",
        #     "bbsSeq": 0,
        #     "storeKeepExclusiveProduct": True,
        #     "naverShoppingRegistration": True,
        #     "channelNo": 0,
        #     "best": True
        # }
        })

    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json;charset=UTF-8',
    'Authorization': f'Bearer {token}'
    }
    conn.request("POST", "/external/v2/products", payload, headers)
    res = conn.getresponse()
    data = res.read()
    print(data.decode("utf-8"))
    decoded_data = data.decode("utf-8")  # 문자열로 디코딩
    parsed = json.loads(decoded_data)    # JSON 파싱

    origin_no = parsed.get("originProductNo")
    smartstore_no = parsed.get("smartstoreChannelProductNo")
    #상품번호 쓰기
    write_productlist(no,origin_no,smartstore_no)

def download_thumb_image(product: Product):
    # original 이미지 URL
    url = product.domeggook_thumb_url
    
    # 현재 파일 기준 상대 경로로 저장 폴더 설정
    base_dir = os.path.join(os.path.dirname(__file__), "SmartStore_image")
    
    # 경로가 없다면 생성
    os.makedirs(base_dir, exist_ok=True)
    
    # 다운로드
    response = requests.get(url)
    if response.status_code == 200:
        file_path = os.path.join(base_dir, "original_image.jpg")
        with open(file_path, "wb") as f:
            f.write(response.content)
        print(f"이미지가 {file_path}로 저장되었습니다.")
    else:
        print("이미지 다운로드 실패:", response.status_code)

def get_upload_imageurl(token):
    url = "https://api.commerce.naver.com/external/v1/product-images/upload"
    # base_dir는 현재 파일 기준 SmartStore_image 폴더
    base_dir = os.path.join(os.path.dirname(__file__), "SmartStore_image")
    
    jpg_path = os.path.join(base_dir, "original_image.jpg")
    png_path = os.path.join(base_dir, "original_image_converted.png")  # 변환 파일 경로

    def upload(file_path, mime_type):
        with open(file_path, 'rb') as f:
            files = {
                'imageFiles': (os.path.basename(file_path), f, mime_type)
            }
            headers = {
                'Accept': 'application/json;charset=UTF-8',
                'Authorization': f'Bearer {token}'
            }
            return requests.post(url, headers=headers, files=files)

    # 1차 시도: JPG 파일 업로드
    mime_type = mimetypes.guess_type(jpg_path)[0] or 'application/octet-stream'
    response = upload(jpg_path, mime_type)

    # 실패 시 PNG 변환 후 재시도
    if not response.ok:
        print(f"1차 업로드 실패. MIME: {mime_type}, PNG로 변환 후 재시도합니다.")
        # JPG → PNG 변환
        try:
            with Image.open(jpg_path) as img:
                img.convert("RGB").save(png_path, "PNG")
        except Exception as e:
            raise Exception(f"이미지 PNG 변환 실패: {e}")

        # PNG 업로드
        response = upload(png_path, 'image/png')

    # 최종 처리
    if response.ok:
        parsed = response.json()
        return parsed["images"][0]["url"]
    else:
        raise Exception(f"업로드 실패: {response.status_code}, {response.text}")

def write_productlist(no,origin_no,smartstore_no):
    # 디렉토리와 파일 경로
    base_dir = os.path.join(os.path.dirname(__file__), "SmartStore_image")
    os.makedirs(base_dir, exist_ok=True)
    
    # product.txt 경로 설정
    filepath = os.path.join(base_dir, "product.txt")
    
    # 파일에 append로 값 저장
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(no + "\n")

    # 파일 경로
    file_path = os.path.join(os.path.dirname(__file__), "product.txt")
    # 파일에 기록
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(f"domeggokNo: {no}, originProductNo: {origin_no}, smartstoreChannelProductNo: {smartstore_no}\n")    
#카탈로그 번호 조회        
def get_categories_no(name_list):
    xml_category_path = ">".join(name_list)
    return xml_category_path

def main():

    # access_token 얻기
    token = get_access_token(client_id, client_secret)
    # 카테고리 가져오기
    categories_no = categories_data(token)

    # 사용할 category 목록 (쉼표로 구분된 문자열)
    # ca_list_str = "12_01_00_00_00,12_01_01_00_00,12_01_02_00_00,12_01_03_00_00,12_01_04_00_00,12_01_05_00_00,12_02_00_00_00,12_02_01_00_00,12_02_02_00_00,12_02_03_00_00,12_02_04_00_00,12_02_05_00_00,12_02_06_00_00,12_02_07_00_00,12_03_00_00_00,12_03_01_00_00,12_03_02_00_00,12_03_03_00_00,12_03_04_00_00,12_03_05_00_00,12_03_06_00_00,12_03_07_00_00,12_03_08_00_00,12_03_09_00_00,12_03_10_00_00,12_03_11_00_00,12_03_12_00_00,12_03_13_00_00,12_04_00_00_00,12_04_01_00_00,12_04_02_00_00,12_04_03_00_00,12_04_03_01_00,12_04_03_02_00,12_04_04_00_00,12_04_05_00_00,12_04_06_00_00,12_04_07_00_00,12_04_08_00_00,12_04_09_00_00,12_04_09_01_00,12_04_09_02_00,12_04_09_03_00,12_04_10_00_00,12_04_10_01_00,12_04_10_02_00,12_04_10_03_00,12_04_10_04_00,12_04_10_05_00,12_04_10_06_00,12_04_10_07_00,12_04_10_08_00,12_04_10_09_00,12_04_10_10_00,12_04_10_11_00,12_04_10_12_00,12_04_10_13_00,12_04_10_14_00,12_04_10_15_00,12_04_10_16_00,12_04_10_17_00,12_04_10_18_00,12_04_11_00_00,12_04_12_00_00,12_04_13_00_00,12_04_14_00_00,12_05_00_00_00,12_05_01_00_00,12_05_02_00_00,12_05_03_00_00,12_05_03_01_00,12_05_03_02_00,12_05_03_03_00,12_05_03_04_00,12_05_04_00_00,12_05_05_00_00,12_05_06_00_00,12_05_07_00_00,12_05_07_01_00,12_05_07_02_00,12_05_08_00_00,12_05_09_00_00,12_05_09_01_00,12_05_09_02_00,12_05_09_03_00,12_05_09_04_00,12_05_09_05_00,12_06_00_00_00,12_06_01_00_00,12_06_01_01_00,12_06_01_02_00,12_06_02_00_00,12_06_02_01_00,12_06_02_02_00,12_06_02_03_00,12_06_02_04_00,12_06_03_00_00,12_06_03_01_00,12_06_03_02_00,12_06_03_03_00,12_06_03_04_00,12_06_03_05_00,12_06_03_06_00,12_06_03_07_00,12_06_04_00_00,12_06_04_01_00,12_06_04_02_00,12_06_04_03_00,12_06_04_04_00,12_06_04_05_00,12_06_04_06_00,12_06_05_00_00,12_06_05_01_00,12_06_05_02_00,12_06_05_03_00,12_06_06_00_00,12_06_06_01_00,12_06_06_02_00,12_06_07_00_00,12_06_07_01_00,12_06_07_02_00,12_06_07_03_00,12_06_07_04_00,12_06_07_05_00,12_06_07_06_00,12_06_07_07_00,12_06_08_00_00,12_06_08_01_00,12_06_08_02_00,12_06_08_03_00,12_06_08_04_00,12_06_08_05_00,12_06_08_06_00,12_06_08_07_00,12_06_09_00_00,12_06_09_01_00,12_06_09_02_00,12_06_10_00_00,12_06_10_01_00,12_06_10_02_00,12_06_10_03_00,12_06_11_00_00,12_06_11_01_00,12_06_11_02_00,12_06_11_03_00,12_06_11_04_00,12_06_12_00_00,12_06_12_01_00,12_06_12_02_00,12_07_00_00_00,12_07_01_00_00,12_07_02_00_00,12_07_03_00_00,12_07_04_00_00,12_07_05_00_00,12_07_06_00_00,12_07_07_00_00,12_07_08_00_00,12_07_09_00_00,12_08_00_00_00,12_08_02_00_00,12_08_02_01_00,12_08_02_02_00,12_08_02_03_00,12_08_02_04_00,12_08_02_05_00,12_08_02_06_00,12_08_02_07_00,12_08_02_08_00,12_08_02_09_00,12_08_02_10_00,12_08_02_11_00,12_08_02_12_00,12_08_03_00_00,12_08_04_00_00,12_08_04_01_00,12_08_04_02_00,12_08_04_03_00,12_08_04_04_00,12_08_04_05_00,12_08_04_06_00,12_08_04_07_00,12_08_04_08_00,12_08_04_09_00,12_08_04_10_00,12_08_04_11_00,12_08_04_12_00,12_08_04_13_00,12_08_04_14_00,12_08_04_15_00,12_08_04_16_00,12_08_05_00_00,12_08_05_01_00,12_08_05_02_00,12_08_05_03_00,12_08_05_04_00,12_08_05_05_00,12_08_05_06_00,12_08_05_07_00,12_08_05_08_00,12_08_05_09_00,12_08_05_10_00,12_08_05_11_00,12_08_05_12_00,12_08_05_13_00,12_08_05_14_00,12_08_05_15_00,12_08_05_16_00,12_08_05_17_00,12_08_05_18_00,12_08_05_19_00,12_08_05_20_00,12_08_05_21_00,12_08_06_00_00,12_08_06_01_00,12_08_06_02_00,12_08_06_03_00,12_08_06_04_00,12_08_06_05_00,12_08_06_06_00,12_08_07_00_00,12_08_07_01_00,12_08_07_02_00,12_08_07_03_00,12_08_07_04_00,12_08_07_05_00,12_08_07_06_00,12_08_07_07_00,12_08_07_08_00,12_08_07_09_00,12_08_08_00_00,12_08_08_01_00,12_08_08_02_00,12_08_08_03_00,12_08_08_04_00,12_08_08_05_00,12_08_08_06_00,12_08_08_07_00,12_08_08_08_00,12_08_08_09_00,12_08_08_10_00,12_08_08_11_00,12_08_08_12_00,12_08_08_13_00,12_08_08_14_00,12_08_08_15_00"
    ca_list_str ="12_01_00_00_00,12_01_01_00_00"
    # 쉼표로 나눠 리스트로 변환
    ca_values = ca_list_str.split(',')
    url = "https://domeggook.com/ssl/api"

    for ca in ca_values:
        
        params = {
            'ver': '4.1',
            'mode': 'getItemList',
            'aid': '5770d1b96006f2b3c91631b6e8d4cadc',
            'market': 'dome',
            'om': 'xml',
            'sz': 10,
            'ca': ca,        # 반복되는 ca 값
            'pg': 1
        }

        response = requests.get(url, params=params)

        if response.status_code == 200:
            root = ET.fromstring(response.text)
            for item in root.findall('.//item'):
                # time.sleep(3)  # 3초간 멈춤
                no = item.findtext('no')
                title = item.findtext('title')
                #올렸던 상품이 아닌 경우
                if not check_and_append_product_no(no):
                    # 도메꾹 상품 조회(detail)
                    product = domeggook_search_product(no,title)
                    #조건이 맞는 상품인 경우만 + 해외배송 아닐때
                    if product and  "+" not in product.price and "false" in product.fromOversea:
                        for item in categories_no:
                            item_parts = item.get("wholeCategoryName").split(">")
                            product_parts = product.categories.split(">")
                            if item_parts[-2:] == product_parts[-2:]:
                                product.smartstore_CategoryId = item.get("id")
                                break
                        #상품 썸네일 다운로드
                        download_thumb_image(product)
                        #상품 이미지 다건 등록
                        product.representativeImage = get_upload_imageurl(token)
                        #상품등록
                        registry_product(token, product,no)
        else:
            print("HTTP 요청 실패:", response.status_code)


    # #올렸던 상품인지 확인
    # check_and_append_product_no(domeggook_product_no)
    # # 도메꾹 상품 조회(detail)
    # product = domeggook_search_product()
    # # access_token 얻기
    # token = get_access_token(client_id, client_secret)

    # #상품 썸네일 다운로드
    # download_thumb_image(product)
    
    # #상품 이미지 다건 등록
    # product.representativeImage = get_upload_imageurl(token)

    # # 상품 데이터 요청
    # # fetch_product_data(token)

    # #카테고리 조회
    # # categories_data(token)

    # #상품등록
    # registry_product(token, product)

    # write_productlist()

if __name__ == "__main__":
    main()
