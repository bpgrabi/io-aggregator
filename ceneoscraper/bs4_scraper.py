from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import requests
import time
import json
import html


def prepare_link(name, category):
    """
    Enter the product name and its category.
    The function returns a link to the search query as a string.
    """
    # fmt: off
    special_characters = [
        "`", "~", "!", "@", "#", "$", "%", "^", "&", "*", "-", "+", "=",
        "{", "}", ":", ";", "|", "\\", '"', "'", ",", "<", ".", ">", "/", "?"
    ]
    # fmt: on
    for char in special_characters:
        name = name.replace(char, "")

    name = " ".join(name.split())  # remove multiple whitespace characters
    link = "https://www.ceneo.pl/" + category + ";szukaj-" + quote_plus(name)

    return link


def get_products(link_to_main_page):
    """
    Enter the link to the search query. The function returns a list of
    dictionaries. The dictionary consists of the id, name and link of one
    product that the user may be interested in.
    """

    content = requests.get(link_to_main_page).text
    soup = BeautifulSoup(content, "lxml")
    products_part = soup.find_all(
        "div",
        class_="category-list-body js_category-list-body "
        "js_search-results js_products-list-main js_async-container",
    )
    products = products_part[0].find_all(
        "div", class_="add-to-favorite__container"
    )  # add to favourite class is always present
    products_names = products_part[0].find_all("strong", class_="cat-prod-row__name")
    products_list = []
    for counter in range(len(products)):
        product_link = "https://ceneo.pl/" + str(products[counter].span["data-pid"])
        product_name = str(products_names[counter].text).strip()
        products_list.append(
            {"id": counter, "name": product_name, "link": product_link}
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

    content = requests.get(website_link).text
    soup = BeautifulSoup(content, "lxml")
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
        product_price = float(".".join(price_tuple))
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

        json_data = requests.get(delivery_data_link).text
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
                "description": product_description,
                "link": product_link,
                "delivery": delivery_list,
            }
        )
        counter += 1

    return offer_list


if __name__ == "__main__":
    start_time = time.time()
    categories = ["", "Zdrowie", "Uroda"]
    entered_string = "neosine"
    ready_link = prepare_link(entered_string, categories[0])
    print(ready_link)
    propos = get_products(ready_link)
    for prop in propos:
        print(prop)

    print("Enter id:")
    idd = 0
    proposition_link = propos[int(idd)].get("link")
    list_of_products = get_offers(proposition_link)
    for element in list_of_products:
        print(element)

    print("Program execution:")
    print("--- %s seconds ---" % (time.time() - start_time))
    print()
    print("Program results:")