import cbpro
import time as time_module
from time import time
import json
import math

auth_client = cbpro.AuthenticatedClient('AUTHENTICATE ACCOUNT HERE')


accounts = {'USD': ['USD-ACCOUNT'], 'BTC': [
    'BTC-ACCOUNT'], 'ETH': ['ETH-ACCOUNT']}

best_btc_price = 0
best_eth_btc_price = 0
best_eth_price = 0
order_info = {}


class myWebsocketClient(cbpro.WebsocketClient):

    def on_open(self):
        self.url = 'wss://ws-feed.pro.coinbase.com/'
        self.api_key = 'API KEY'
        self.api_secret = 'API SECRET'
        self.api_passphrase = 'API PASSPHRASE'
        self.auth = True
        self.products = ['BTC-USD', 'ETH-BTC', 'ETH-USD']
        self.channels = ['user', 'ticker']
        self.message_count = 0

    def on_message(self, msg):
        self.message_count += 1
        global best_btc_price
        global best_eth_btc_price
        global best_eth_price
        global order_info

        if ('order_id' in msg):
            order_info = msg

        elif (msg['type'] == 'ticker'):
            if (msg['product_id'] == 'BTC-USD'):
                best_btc_price = msg['best_ask']
            elif (msg['product_id'] == 'ETH-BTC'):
                best_eth_btc_price = msg['best_ask']
            elif (msg['product_id'] == 'ETH-USD'):
                best_eth_price = msg['best_bid']

    def on_close(self):
        print('-- Goodbye! --')


def round_down(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n * multiplier) / multiplier


def get_prices(btcusd, ethbtc, usdeth):
    first_fees = 0
    second_fees = 0
    third_fees = 0
    total_fees = 0
    taker_fee = .005

    # Crazy stuff to account for fees. Subtracting the amount of BTC equal to the fee cost in order to purchase the correct amount we can afford.
    first_fees += round((aum * taker_fee), 2)
    btc_to_buy = round(
        (aum-.01)/(float(btcusd)) - ((first_fees)/float(btcusd)), 8)

    # Fees on second transaction. Subtracts the amount of ETH equal to the fee cost in order to purchase what we can actually afford.
    second_fees += round((btc_to_buy * taker_fee), 8)
    eth_to_buy = round(
        (btc_to_buy)/(float(ethbtc)) - ((second_fees)/float(ethbtc)), 5)

    third_fees += round(((eth_to_buy*(float(usdeth))) * taker_fee), 2)
    eth_to_usd = eth_to_buy*(float(usdeth)) - third_fees

    total_fees += round((first_fees +
                         round((second_fees * float(btcusd)), 2) + third_fees), 2)

    return_values = {'BTC_PRICE': [], 'ETH_PRICE': [], 'ETH_USD_PRICE': [], 'BTC_TO_BUY': [
    ], 'ETH_TO_BUY': [], 'FEES': [], 'RETURNS': []}
    return_values['BTC_PRICE'] = float(btcusd)
    return_values['ETH_PRICE'] = float(ethbtc)
    return_values['ETH_USD_PRICE'] = float(usdeth)
    return_values['BTC_TO_BUY'] = btc_to_buy
    return_values['ETH_TO_BUY'] = eth_to_buy
    return_values['FEES'] = total_fees
    return_values['RETURNS'] = round(eth_to_usd, 2)

    print('\n' + 'Fees: $' + str(total_fees))
    print('Returns: $' + str(return_values['RETURNS']) + '\n')

    return return_values


def usd_to_btc(order_size, order_price):

    if (place_order('buy', 'BTC-USD', order_size, order_price, True)):
        print('USD to BTC: Complete')
        return 1
    else:
        print('Failed to buy BTC with USD')
        return 0


def btc_to_eth(order_size, order_price):

    if (place_order('buy', 'ETH-BTC', order_size, order_price, False)):
        print('BTC to ETH: Complete')
        return 1
    else:
        print('Failed to buy ETH with BTC')
        return 0


def eth_to_usd(order_size, order_price):

    if (place_order('sell', 'ETH-USD', order_size, order_price, False)):
        print('ETH to USD: Complete')
        return 1
    else:
        print('Failed to sell ETH for USD')
        return 0


def place_order(side, product, size, price, fok):
    if (fok):
        tif = 'FOK'
    else:
        tif = 'GTC'

    new_order = auth_client.place_limit_order(
        side=side, product_id=product, size=size, price=price, time_in_force=tif)

    if ('id' not in new_order):
        print(new_order)
        print(size)
        print(price)
        return 0

    while(order_info == {} or order_info['type'] != 'done'):
        None

    return 1


#########################################################################################################################################
# Main code below.
if __name__ == '__main__':

    try:

        trade_count = 0

        wsClient = myWebsocketClient()
        wsClient.start()

        while (best_btc_price == 0 or best_eth_btc_price == 0 or best_eth_price == 0):
            time_module.sleep(1)

        while (0 < 1):

            aum = round_down(float(auth_client.get_account(
                account_id=accounts['USD'][0])['available']), 2)

            print('############################################################################################################################')

            returns = get_prices(
                best_btc_price, best_eth_btc_price, best_eth_price)

            if (returns['RETURNS'] > (aum - returns['FEES'])):
                print('Arbitrage Executed: $' + str(aum) +
                      ' to $' + str(returns['RETURNS']) + '\n')

                start = time()

                if (usd_to_btc(returns['BTC_TO_BUY'], returns['BTC_PRICE'])):

                    order_info.clear()

                    if (btc_to_eth(returns['ETH_TO_BUY'], returns['ETH_PRICE'])):

                        order_info.clear()

                        if (eth_to_usd(returns['ETH_TO_BUY'], returns['ETH_USD_PRICE'])):

                            order_info.clear()
                            trade_count += 1
                            print('\nDuration: {0:.2f}s'.format(
                                time()-start))
                            aum = round_down(float(auth_client.get_account(
                                account_id=accounts['USD'][0])['available']), 2)

            else:
                print('No Arbitrage Detected' + '\n')

            print('\n' + 'Current AUM: $' + str(aum))
            print('Trades Executed: ' + str(trade_count) + '\n')

            time_module.sleep(1)

    except KeyboardInterrupt:
        wsClient.close()
        SystemExit
