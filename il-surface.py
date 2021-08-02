from uniswap import Uniswap
import pandas as pd
import numpy as np
from scipy import interpolate
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from dotenv import dotenv_values

address = None         # or None if you're not going to make transactions
private_key = None  # or None if you're not going to make transactions
version = 3                       # specify which version of Uniswap to use
# can also be set through the environment variable `PROVIDER`
provider = dotenv_values(".env")["WEB3"]
uniswap = Uniswap(address=address, private_key=private_key,
                  version=version, provider=provider)

eth = "0x0000000000000000000000000000000000000000"
usdc = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"


def getPrice(token):
    price = uniswap.get_price_input(token, usdc, 10**18) / 1e6
    return price


def iloss_simulate(base_token=usdc, quote_token=eth, value=100, base_pct_chg=0, quote_pct_chg=0):
    """Calculate simulated impermanent loss from an initial value invested, get real time prices from pancakeswap API
        This method create a 3D interpolated surface for impermanent loss and initial/final value invested"""

    # get real time prices
    px_base = 1 ## price of usdc
    px_quote = getPrice(quote_token)

    # Prepare grid
    q_base, q_quote = (value/2)/px_base,  (value/2)/px_quote
    px_base, px_quote, q_base, q_quote
    # @dev deviate px_base very slightly, so plot works
    pxs_base = [px_base+i*0.00001 for i in range(1,301)]
    pxs_quote = [px_quote*i/100 for i in range(1, 301)]
    rows = []
    for px_b in pxs_base:
        for px_q in pxs_quote:
            ratio = (px_b / px_base) / (px_q / px_quote)
            iloss = 2 * (ratio**0.5 / (1 + ratio)) - 1

            row = {'px_base': px_b, 'px_quote': px_q,
                   'ratio': (px_b / px_base) / (px_q / px_quote),
                   'impremante_loss': iloss}
            rows.append(row)
    df = pd.DataFrame(rows)
    df_ok = df.loc[:, ['px_base', 'px_quote', 'impremante_loss']]
    df_ok = df_ok.replace('NaN', np.nan).dropna()

    if all(isinstance(i, (int, float)) for i in (value, base_pct_chg, quote_pct_chg)):
        px_base_f = px_base * (1+base_pct_chg/100)
        px_quote_f = px_quote * (1+quote_pct_chg/100)
        ratio = (px_base_f / px_base) / (px_quote_f / px_quote)
        iloss = 2 * (ratio**0.5 / (1 + ratio)) - 1
        value_f = (px_base_f*q_base + px_quote_f * q_quote) * (iloss+1)
    else:
        px_base_f, px_quote_f = px_base, px_quote
        iloss = 0
        value_f = None
        print('must input numerical amount and pct change for base and quote to calculations of final value')

    # Ploting surface
    fig = plt.figure(figsize=(8, 8))
    x1 = np.linspace(df_ok['px_base'].min(), df_ok['px_base'].max(), len(
        df_ok['px_base'].unique()))
    y1 = np.linspace(df_ok['px_quote'].min(), df_ok['px_quote'].max(), len(
        df_ok['px_quote'].unique()))
    x2, y2 = np.meshgrid(x1, y1)
    Z = interpolate.griddata(
        (df_ok['px_base'], df_ok['px_quote']), df_ok['impremante_loss'], (x2, y2))
    Z[np.isnan(Z)] = df_ok.impremante_loss.mean()
    ax = plt.axes(projection='3d', alpha=0.2)

    ## flip x and y
    ax.plot_wireframe(x2, y2, Z, color='tab:blue',
                      lw=1, cmap='viridis', alpha=0.6)

    # Start values ploting
    xmax = df_ok.px_base.max()
    ymax = df_ok.px_quote.max()

    ## plotting the wires
    # ax.plot([px_base, px_base], [0, px_quote], [-1, -1], ls='--', c='k', lw=1)
    ax.plot([px_base, px_base], [px_quote, px_quote],
            [0, -1], ls='--', c='k', lw=1)
    # ax.plot([px_base, 0], [px_quote, px_quote], [-1, -1], ls='--', c='k', lw=1)

    # # End values ploting
    # ax.plot([px_base_f, px_base_f], [0, px_quote_f],
    #         [-1, -1], ls='--', c='gray', lw=1)
    # ax.plot([px_base_f, px_base_f], [px_quote_f, px_quote_f],
    #         [iloss, -1], ls='--', c='gray', lw=1)
    # ax.plot([px_base_f, 0], [px_quote_f, px_quote_f],
    #         [-1, -1], ls='--', c='gray', lw=1)
    # ax.plot([px_base_f, px_base_f], [px_quote_f, ymax],
    #         [iloss, iloss], ls='--', c='gray', lw=1)
    # ax.plot([px_base_f, 0], [ymax, ymax], [
    #         iloss, iloss], ls='--', c='gray', lw=1)

    # Plot settings
    # Colorbar only for plot_surface() method instead plot_wireframe()
    # m = cm.ScalarMappable(cmap=cm.viridis)
    # m.set_array(df_ok['impremante_loss'])
    # plt.colorbar(m, fraction=0.02, pad=0.1)
    x, y, z = (px_base, px_quote, .05)
    p = ax.scatter(x, y, z, c='k', marker='v', s=300)
    ax.set_title('Impermanent Loss Surface', y=0.95)
    ax.set_xlabel(f'Price USDC', labelpad=15.0)
    ax.set_ylabel(f'Price ETH', labelpad=10.0)
    ax.set_zlabel('Impermanent loss', labelpad=1.0)
    ax.view_init(elev=25, azim=-165)  # start view angle

    print(
        f"\nStart value USD {value:.0f}, {base_token} USD {px_base:.2f}, {quote_token} USD {px_quote:.2f}")
    print(
        f"\nResults assuming {base_token.upper()} {base_pct_chg}%, and {quote_token.upper()} {quote_pct_chg}%")
    print(f"End value estimate USD {value_f:.0f}, iloss: {iloss:.2%}")
    plt.show()

    return value_f, iloss


iloss_simulate(value=1000, base_pct_chg=0, quote_pct_chg=25)
