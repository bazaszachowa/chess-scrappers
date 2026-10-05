import re
from threading import Semaphore
from typing import Any
from urllib.parse import urlparse, urlsplit, urlunsplit

import requests
from unidecode import unidecode

download_semaphore = Semaphore(2)
TIMEOUT = 10


def lichess_download(link: str) -> str:
    res = requests.get(link, timeout=TIMEOUT)
    if res.ok:
        link = res.url
    parts = urlsplit(link)
    link = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    match = re.search(
        r"^https://lichess\.org/team/",
        link,
    )
    if match:
        return ""

    pgn = ""
    with download_semaphore:
        ids = set()
        match = re.search(r"https://lichess\.org/broadcast/([^/?#]+)$", link)
        lichess_url = None
        if match:
            lichess_url = "https://lichess.org/api/broadcast/" + match.group(1)

        match = re.search(
            r"https://lichess\.org/broadcast/([^/?#]+/[^/?#]+/[^/?#]+)(/[^/?#]+)?$",
            link,
        )
        if match:
            lichess_url = "https://lichess.org/api/broadcast/" + match.group(1)

        if lichess_url:
            response = requests.get(lichess_url, timeout=TIMEOUT)
            if response.ok:
                data = response.json()

                for tour in data.get("group", {}).get("tours", []):
                    ids.add(tour["id"])

                if data.get("tour"):
                    ids.add(data["tour"]["id"])

                for tour_id in ids:
                    res = requests.get(
                        f"https://lichess.org/api/broadcast/{tour_id}.pgn",
                        timeout=TIMEOUT,
                    )
                    if res.ok:
                        pgn += res.text + "\n\n"

        else:
            raise ValueError(f"Incorrect lichess URL: {link}")

        return unidecode(pgn)


def scrap_livechess(url: str) -> str:
    pgn = ""
    parsed_url = urlparse(url)
    tournament_id = parsed_url.fragment
    tournament_response = requests.get(
        f"https://1.pool.livechesscloud.com/get/{tournament_id}/tournament.json",
        timeout=TIMEOUT,
    )
    tournament_json = tournament_response.json()
    rounds = tournament_json["rounds"]
    for i in range(len(rounds)):
        round_response = requests.get(
            f"https://1.pool.livechesscloud.com/get/{tournament_id}/round-{i + 1}/index.json",
            timeout=TIMEOUT,
        )
        round_json = round_response.json()
        for j in range(len(round_json["pairings"])):
            response = requests.get(
                f"https://1.pool.livechesscloud.com/get/{tournament_id}/round-{i + 1}/game-{j + 1}.json?poll",
                timeout=TIMEOUT,
            )
            if response.ok:
                metadata = round_json["pairings"][j]
                metadata["date"] = round_json["date"]
                metadata["round"] = i + 1
                metadata.update(tournament_json)
                pgn += json2pgn(response.json(), metadata)
    return unidecode(pgn)


def json2pgn(data: dict[str, Any], metadata: dict[str, Any]) -> str:
    tournament = (metadata.get("name", None) or "?").replace('"', "")
    site = (metadata.get("location", None) or "?").replace('"', "")
    date = (metadata.get("date", None) or "????.??.??").replace("-", ".")

    if metadata["white"]:
        white_parts = []
        if metadata["white"]["lname"]:
            white_parts.append(metadata["white"]["lname"].replace('"', ""))
        if metadata["white"]["fname"]:
            white_parts.append(metadata["white"]["fname"].replace('"', ""))
        white = ", ".join(white_parts)
    else:
        white = "N, N"

    if metadata["black"]:
        black_parts = []
        if metadata["black"]["lname"]:
            black_parts.append(metadata["black"]["lname"].replace('"', ""))
        if metadata["black"]["fname"]:
            black_parts.append(metadata["black"]["fname"].replace('"', ""))
        black = ", ".join(black_parts)
    else:
        black = "N, N"

    moves = ""
    for i in range(len(data["moves"])):
        if i % 2 == 0:
            moves += str(i // 2 + 1) + ". "
        moves += data["moves"][i].split(" ")[0] + " "
    moves += metadata["result"]
    return f"""
[Event "{tournament or "?"}"]
[Site "{site or "?"}"]
[Date "{date}"]
[Round "{metadata["round"] or "?"}"]
[White "{white or "N, N"}"]
[Black "{black or "N, N"}"]
[Result "{metadata["result"] or "*"}"]
{moves}
"""
