import hyperliquid_bot.util_funcs as n
import dontshare as d 
from eth_account.signers.local import LocalAccount
import eth_account
import json, time 
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import ccxt 
import pandas as pd
import datetime
import schedule
import requests

'''variables'''
# # #
symbol = "WIF"
max_loss = -5
target = 4
acct_min = 9
timeframe = '4h'
size = 10
coin = symbol 
secret_key = d.private_key
account = LocalAccount = eth_account.Account.from_key(secret_key)
def get_position(symbol, account):
    '''gets the position info we need'''
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    user_state = info.user_state(account.address)
    print(f'this is the current account val {user_state["marginSummary"]["accountValue"]}')
    positions = []
    print(f'this is the symbol {symbol}')
    for position in user_state['assetPositions']:
        if (position['position']['coin'] == symbol and float(position["position"]['szi']) != 0):
            positions.append(position['position'])
            in_pos = True
            size = float(position["position"]['szi'])
            pos_sym = position["position"]['coin']
            entry_px = float(position['position']['entryPx'])
            pnl_perc = float(position['position']['returnOnEquity'])*100 
            print(f'this is the pnl perc {pnl_perc}')
            break
    else:
        in_pos = False
        size = 0
        pos_sym = None
        entry_px = 0
        pnl_perc = 0
    if size > 0:
        Long = True
    elif size < 0:
        Long = False
    else:
        Long = None
    return positions, in_pos, size, pos_sym, entry_px, pnl_perc, Long 

def get_sz_px_decimals(symbol):
    ''' this returns size and price decimals '''
    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type':'application/json'}
    data = {'type': 'meta'}
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        data = response.json()
        symbols = data['universe']
        symbol_info = next((s for s in symbols if s['name'] == symbol), None)
        if symbol_info:
            sz_decimals= symbol_info['szDecimals'] 
        else:
            print('symbol not found')
    else:
        print('Error', response.status_code)
    ask = ask_bid(symbol)[0]
    ask_str = str(ask)
    
    if '.' in ask_str:
        px_decimals = len(ask_str.split('.')[1])
    else:
        px_decimals = 0
    print(f'{symbol} is the price {sz_decimals} decimals')

    return sz_decimals, px_decimals

def ask_bid(symbol):
    '''this gets the ask and bid price for any symbol passed in'''
    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type':'application/json'}
    data = {
        'type':'l2Book',
        'coin': symbol
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    l2_data = response.json()
    l2_data = l2_data['levels'] 

    # get ask bid 
    bid= float(l2_data[0][0]['px']) 
    ask = float(l2_data[1][0]['px']) 
    return ask, bid, l2_data

def limit_order(coin, is_buy, sz, limit_px, reduce_only, account):
    exchange = Exchange(account, constants.MAINNET_API_URL)
    rounding = get_sz_px_decimals(coin)[0]
    sz = round(sz, rounding)
    print(f'coin:{coin}, type: {type(coin)}')
    print(f'is_buy: {is_buy}, type:{type(coin)}')
    print(f'sz: {sz}, type:{type(limit_px)}')
    print(f'reduce_only:{reduce_only}, type:{type(reduce_only)}')
    print(f'placing limit order for {coin} {sz} @ {limit_px}')
    order_result = exchange.order(coin, is_buy, sz, limit_px, {'limit':{"tif":'Gtc'}}, reduce_only=reduce_only)
    print(order_result)
    
    if is_buy:
        print(f"limit BUY order placed, resting:{order_result['response']['data']['statuses'][0]}")
    else:
        print(f"limit SELL order placed, resting:{order_result['response']['data']['statuses'][0]}")

    return order_result

def cancel_orders(account):
    exchange = Exchange(account, constants.MAINNET_API_URL)
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    open_orders = info.open_orders(account.address)
    print(f'open orders:\n')
    for open_order in open_orders:
        print(f'cancelling order {open_order}')
        exchange.cancel(open_order['coin'], open_order['oid'])
        


def kill_switch(symbol, account):
    positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, Long = get_position(symbol, account)
    while im_in_pos:
        cancel_orders(account)
        # get bid ask 
        ask, bid, l2_data = ask_bid(pos_sym)
        pos_size = abs(pos_size)
        if Long:
            limit_order(pos_sym, False, pos_size, ask, True, account)
            print('kill switch sell to close submitted')
            time.sleep(5)
        elif Long == False:
            limit_order(pos_sym, True, pos_size, bid, True, account)
            print('kill swtich buy to close submitted')
            time.sleep(5)

    positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, Long = get_position(symbol, account)

    
def pnl_close(symbol, target, max_loss, account):
    '''checks if our trade hit target or max loss'''
    print('entering pnl close')
    positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, Long = get_position(symbol, account)
    if (pnl_perc > target):
        print(f'pnl gain is {pnl_perc} and target is {target} closing position as a win')
        kill_switch(pos_sym, account)
    elif (pnl_perc <= max_loss):
        print(f'pnl loss is {pnl_perc} and max loss is {max_loss} and closing position as a loss')
        kill_switch(pos_sym, account)
    else:
        print(f'pnl loss is {pnl_perc} and max loss is {max_loss} and target {target} not closing')
    print('finished pnl close')


def acct_bal(account):
    account = LocalAccount = eth_account.Account.from_key(secret_key)
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    user_state = info.user_state(account.address)
    return user_state['marginSummary']['accountValue']
