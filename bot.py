import discord
from discord.ext import commands
import requests
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
alerts = []


def get_coordinates(city):
    geo_url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1"

    headers = {
        "User-Agent": "DiscordFuelBot"
    }

    response = requests.get(geo_url, headers=headers)
    data = response.json()

    print("GEO RESPONSE:", data)

    if len(data) == 0:
        return None

    lat = data[0]["lat"]
    lng = data[0]["lon"]

    return lat, lng


def get_prices(city):
    coordinates = get_coordinates(city)

    if coordinates is None:
        return "CITY_NOT_FOUND"

    lat, lng = coordinates

    url = f"https://creativecommons.tankerkoenig.de/json/list.php?lat={lat}&lng={lng}&rad=10&sort=price&type=diesel&apikey={API_KEY}"

    response = requests.get(url)
    data = response.json()

    print("API RESPONSE:", data)

    if "stations" not in data:
        return None

    return data["stations"][:5]


@bot.command()
async def alert(ctx, city, target_price: float):
    alerts.append({
        "user": ctx.author,
        "city": city,
        "target": target_price
    })

    await ctx.send(
        f"Alert created for {city.title()} below €{target_price}"
    )


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.command()
async def price(ctx, *, city):
    stations = get_prices(city)

    if stations == "CITY_NOT_FOUND":
        await ctx.send("City not supported.")
        return

    if stations is None:
        await ctx.send("API error.")
        return

    message = f"⛽ Cheapest diesel prices in {city.title()}:\n\n"

    for s in stations:
        message += f"{s['name']} - €{s['price']}\n{s['street']}\n\n"

    await ctx.send(message)


async def check_alerts():
    await bot.wait_until_ready()
    print("Alert loop running...")

    while not bot.is_closed():
        for alert in alerts:
            stations = get_prices(alert["city"])

            if stations is None or stations == "CITY_NOT_FOUND":
                continue

            cheapest = stations[0]["price"]

            if cheapest <= alert["target"]:
                user = alert["user"]

                await user.send(
                    f"⛽ ALERT!\n\nDiesel in {alert['city'].title()} is now €{cheapest}"
                )

        await asyncio.sleep(30)


async def main():
    async with bot:
        bot.loop.create_task(check_alerts())
        await bot.start(DISCORD_TOKEN)


asyncio.run(main())