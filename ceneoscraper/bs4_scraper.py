from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import requests
import time
import json
import html
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pl,en-US,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
    "TE": "trailers",
}


def prepare_link(name, category):
    """
    Enter the product name and its category.
    The function returns a sanitized link to the search query as a string.
    """
    # fmt: off
    special_characters = [
        "`", "~", "#", "%", "^", "&", "*", "-", "+", "=", "{", "}",
        ":", ";", "|", "\\", '"', "'", ",", "<", ".", ">", "/", "?"
    ]
    # fmt: on
    for char in special_characters:
        name = name.replace(char, " ")

    name = (
        " ".join(name.split()).strip().lower()
    )  # remove multiple whitespace characters, lower case, and strip
    link = "https://www.ceneo.pl/" + category + ";szukaj-" + quote_plus(name)

    return link


def get_products(link_to_main_page, option):
    """
    Enter the link and option to the search query. The function returns a list of
    dictionaries. The dictionary consists of the id, name, product url,
    image url, the lowest price and shop url.

    Options:
    1 - all shops
    2 - only allegro
    3 - any shop without allegro

    Shop url takes value "" when you can buy product at least in 2 shops or name of
    shop when you can buy product in exactly 1 shop.
    """

    if option == 2:
        link_to_main_page = link_to_main_page + ";20136-0v.htm"

    # Disallow redirects which can occur in two cases:
    # 1. when only a single product is found
    # 2. when the search result is empty the category is removed
    request = requests.get(link_to_main_page, allow_redirects=False, headers=headers)

    # category is present between the "/" and ";" characters
    # if they are present together, it means that the category
    # has been removed from the url via a redirect
    if (
        request.status_code == 302
        and "/;" in request.headers["Location"]  # category removed
        or request.status_code == 500  # invalid request, e.g. too short
        or request.status_code == 301  # e.g. empty string
    ):
        return None

    content = request.text
    soup = BeautifulSoup(content, "lxml")
    products_part = soup.find_all(
        "div",
        class_="category-list-body js_category-list-body "
        "js_search-results js_products-list-main js_async-container",
    )
    products = products_part[0].find_all(
        "div", class_=re.compile("cat-prod-row js_category-list-item.*")
    )

    products_names = products_part[0].find_all("strong", class_="cat-prod-row__name")
    products_images = products_part[0].find_all("div", class_="cat-prod-row__foto")
    products_price = products_part[0].find_all("div", class_="cat-prod-row__price")
    products_list = []
    for counter in range(len(products)):
        try:
            product_link = "https://ceneo.pl/" + str(products[counter].span["data-pid"])
        except KeyError:
            product_link = "https://ceneo.pl/" + str(products_names[counter].a["href"])

        if "https://ceneo.pl//Click/Offer/?e" in product_link:
            try:
                product_link = "https://ceneo.pl/" + str(products[counter]["data-pid"])
            except KeyError:
                product_link = "https://ceneo.pl/" + str(
                    products_names[counter].a["href"]
                )

        product_name = str(products_names[counter].text).strip()
        value = products_price[counter].find("span", class_="value").text
        penny = products_price[counter].find("span", class_="penny").text
        price_tuple = (str(value), str(penny)[1:])
        product_price = float(".".join(price_tuple).replace(" ", ""))

        # each element has the "src", but only the first few img tags contain link to the image,
        # the rest of the images are generated using javascript and "data-original" fields
        # (not every element has them)
        try:
            product_image = "https:" + products_images[counter].a.img["data-original"]
        except KeyError:
            product_image = "https:" + products_images[counter].a.img["src"]

        shop_url = ""
        if option == 2:
            shop_url = "allegro.pl"
        elif option == 1 or option == 3:
            try:
                shop_numb = (
                    products_price[counter].find("span", class_="shop-numb").text
                )
                shop_numb = (shop_numb.split())[1]
                shop_numb = int(shop_numb.strip())
            except (AttributeError, IndexError):
                shop_numb = 1

            if shop_numb is None or shop_numb == "":
                shop_numb = 1

            shop_url = ""
            if shop_numb == 1:
                try:
                    shop_url = products[counter]["data-shopurl"]
                except KeyError:
                    shop_url = ""

                if "https://" in shop_url:
                    shop_url = shop_url.removeprefix("https://")
                elif "http://" in shop_url:
                    shop_url = shop_url.removeprefix("http://")

            if option == 3:
                if shop_numb == 1:
                    if "allegro" in shop_url:
                        continue
                    elif shop_url == "":
                        try:
                            offer = get_offers(product_link)
                            shop_url = offer[0]["shop_url"]
                        except (Exception,):
                            shop_url = ""

                        if "allegro" in shop_url or shop_url == "" or shop_url is None:
                            continue

            if option == 1 and shop_numb == 1:
                if shop_url == "" or shop_url is None:
                    try:
                        offer = get_offers(product_link)
                        shop_url = offer[0]["shop_url"]
                    except (Exception,):
                        shop_url = ""

                    if shop_url == "" or shop_url is None:
                        continue

        products_list.append(
            {
                "id": counter,
                "name": product_name,
                "link": product_link,
                "image": product_image,
                "price": product_price,
                "shop_url": shop_url,
            }
        )

    return products_list


def get_offers(website_link):
    """
    Enter the link to specific product on Ceneo. The function returns a list
    of dictionaries. The dictionary consists of the id, price, shop URL /
    shop name, description, link and list of dictionaries containing
    delivery possibilities of one offer where you can buy the product. List
    of dictionaries containing delivery possibilities consists of delivery
    name, cost and payment method.
    """

    content = requests.get(website_link, headers=headers).text
    soup = BeautifulSoup(content, "lxml")
    offers_proposed_by_ceneo = soup.find_all(
        "ul", class_="product-offers__list js_product-offers"
    )
    if offers_proposed_by_ceneo is None:
        offers_proposed_by_ceneo = ""
    pattern = re.compile(r"\.remainingInit\('(.*)',")
    hidden_offers_script = soup.find_all("script", text=pattern)
    if hidden_offers_script:
        matching_text = pattern.search(html.unescape(hidden_offers_script[0].text))
        if matching_text:
            hidden_offers_link = "https://www.ceneo.pl/"
            hidden_offers_link += str(
                json.loads('{"s":"' + matching_text.group(1) + '"}')["s"]
            )
            content = requests.get(hidden_offers_link, headers=headers).text
            soup = BeautifulSoup(str(str(offers_proposed_by_ceneo) + content), "lxml")

    offers = soup.find_all(
        "li", class_="product-offers__list__item js_productOfferGroupItem"
    )
    counter = 0
    offer_list = []
    for offer in offers:
        details = offer.find(
            "div",
            class_="product-offer__product js_product-offer__product "
            "js_productName specific-variant-content",
        )
        product_description = details.div.a.span.text
        product_link = "https://ceneo.pl" + str(details.div.a["href"])
        value = details.find("span", class_="value").text
        penny = details.find("span", class_="penny").text
        price_tuple = (str(value), str(penny)[1:])
        shop_image = offer.find("div", class_="product-offer__store__logo")

        # each element has the "src", but only the first few img tags contain link to the image,
        # the rest of the images are generated using javascript and "data-original" fields
        # (not every element has them)
        try:
            shop_image = "https:" + shop_image.a.img["data-original"]
        except KeyError:
            shop_image = "https:" + shop_image.a.img["src"]

        product_price = float(".".join(price_tuple).replace(" ", ""))
        try:
            shop_url = offer.div.div["data-shopurl"]
            delivery_data_link = (
                "https://www.ceneo.pl/Product/GetOfferDetails?data="
                + product_link.split("?e=", 1)[1]
            )
        except KeyError:
            shop_name_section = offer.find(
                "ul", "product-offer__details__toolbar__links"
            )
            shop_name = shop_name_section.find_all("li")
            shop_url = (shop_name[-1].text.split())[-1]
            html_frag = offer.find(
                "span",
                class_="product-delivery-info js_deliveryInfo js_hide-buy-in-shop",
            )
            html_frag = str(html_frag["data-info-hook"])
            delivery_data_link = (
                "https://www.ceneo.pl/Product/GetOfferDetails?data=" + html_frag
            )
        json_data = requests.get(delivery_data_link, headers=headers).text
        parsed = json.loads(json_data)
        deliver_html = html.unescape(parsed["ProductDetailsAdditionalPartial"])
        delivery_soup = BeautifulSoup(deliver_html, "lxml")
        deliveries = delivery_soup.find_all(
            "li",
            class_="product-offer-details__additional__delivery-costs__list__item",
        )
        delivery_list = []
        for delivery in deliveries:
            payment_method = delivery.find(
                "div",
                class_="product-offer-details__additional"
                "__delivery-costs__list__item__type",
            )
            payment_method = payment_method.text.strip()
            if payment_method != "Przewidywany czas dostawy:":
                delivery_options_section = delivery.find(
                    "ul",
                    class_="product-offer-details__additional"
                    "__delivery-costs__list__item__options",
                )
                delivery_option_list = delivery_options_section.find_all("li")
                for option in delivery_option_list:
                    delivery_cost = option.b.text
                    delivery_cost = delivery_cost[:-3]
                    delivery_cost = delivery_cost.replace(",", ".")
                    delivery_cost = float(delivery_cost)
                    delivery_name = option.text.split()
                    delivery_name = " ".join(delivery_name[2:])
                    delivery_list.append(
                        {
                            "delivery_name": delivery_name,
                            "delivery_cost": delivery_cost,
                            "payment_method": payment_method,
                        }
                    )

        offer_list.append(
            {
                "id": counter,
                "price": product_price,
                "shop_url": shop_url,
                "shop_image": shop_image,
                "description": product_description,
                "link": product_link,
                "delivery": delivery_list,
            }
        )
        counter += 1
    if len(offers) != 1:
        time.sleep(6)
    return offer_list
