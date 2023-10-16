"""
Email all users of the game the results of the round.

Since the webapp version came live this is not used anymore so it may not be up to date.
"""

import sys
from collections import defaultdict
import fnmatch
import smtplib
import ssl
from jinja2 import Environment, FileSystemLoader
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from cfg import *
from engine.gamedirectory import GameDirectory

SHIP_NAME_POS = 0
PLAYER_NAME_POS = 4

# Email config file is expected:
# (sender email)
# (app password)
# and then further lines:
# (Player name) (Email)


def send_email(game_dir: GameDirectory, round_name: str, result_file_name: str, player_name: str, ship_name: str, round_number: int, send_manual: bool):
    email_password, email_sender, player_emails = load_email_config(game_dir.email_file)

    if player_name not in player_emails:
        sys.exit(f"Player {player_name} not found in email list to send {result_file_name}.")
    email_receiver = player_emails[player_name]

    print(f"Sending {result_file_name} to {player_name} email {email_receiver}")

    em = MIMEMultipart('mixed')
    em['From'] = email_sender
    em['To'] = player_emails[player_name]
    em['Subject'] = f"[Space Arena] {game_dir.game_name}/{result_file_name}"

    # Email Body
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(ROUND_EMAIL_TEMPLATE)

    template_data = {
        "name": player_name,
        "round_nr": str(round_number),
        "next_round_deadline": 'TBD'
    }

    body = MIMEText(template.render(template_data), 'html')
    em.attach(body)

    # Attachment: Report PDF
    with open(os.path.join(game_dir.path, round_name, result_file_name), "rb") as attachment:
        p = MIMEApplication(attachment.read(), _subtype="pdf")
        p.add_header('Content-Disposition', "attachment", filename=result_file_name)
        em.attach(p)

    # Attachment: Command file template
    with open(os.path.join(TEMPLATE_DIR, SHIP_COMMAND_TEMPLATE)) as f:
        attachment = MIMEText(f.read())
    command_template_name = COMMAND_FILE_TEMPLATE.format(ship_name, str(round_number + 1))
    attachment.add_header('Content-Disposition', 'attachment', filename=command_template_name)
    em.attach(attachment)

    if send_manual:
        # Attachment: Manual
        with open(MANUAL_FILENAME, "rb") as attachment:
            p = MIMEApplication(attachment.read(), _subtype="pdf")
            p.add_header('Content-Disposition', "attachment", filename=MANUAL_FILENAME)
            em.attach(p)

    # Send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(email_sender, email_password)
        smtp.sendmail(email_sender, email_receiver, em.as_string())


def load_email_config(email_cfg):
    with open(email_cfg) as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        email_sender = lines[0]
        email_password = lines[1]
        player_emails = {name: email for name, email in [line.split() for line in lines[2:]]}
    return email_password, email_sender, player_emails


def check_ok_to_send(game_directory: GameDirectory):
    # Check if all is okay
    game_directory.check_ok()
    player_emails = load_email_config(game_directory.email_file)[2]
    player_ships = load_init_file(game_directory.init_file)
    emails_not_present = list()
    for player_name in player_ships.keys():
        if player_name not in player_emails:
            emails_not_present.append(player_name)
    if len(emails_not_present) > 0:
        sys.exit(f"Player(s) {''.join(emails_not_present)} email address not found in email config file.")


def send_results_for_round(game_directory: GameDirectory, round_number: int, include_manual: bool):
    player_ships = load_init_file(game_directory.init_file)

    # For each player, for each ship, send one email
    round_name = f"round-{round_number}"
    round_dir = os.path.join(game_directory.path, round_name)
    round_contents = os.listdir(round_dir)
    for name, ship_names in player_ships.items():
        for ship_name in ship_names:
            result_files = fnmatch.filter(round_contents, f"{ship_name}-{round_name}.pdf")
            if len(result_files) > 1:
                sys.exit(f"Got multiple results for {ship_name} in round {round_number}: {result_files}")
            elif len(result_files) == 1:
                send_email(game_dir=game_directory,
                           round_name=round_name,
                           result_file_name=result_files[0],
                           player_name=name,
                           ship_name=ship_name,
                           round_number=round_number,
                           send_manual=include_manual)


def load_init_file(init_file_name):
    # Collect ships per player
    player_ships = defaultdict(list)
    with open(init_file_name) as f:
        lines = [line.strip().split(' ') for line in f.readlines() if line.strip()]
        for line in lines:
            player_ships[line[PLAYER_NAME_POS]].append(line[SHIP_NAME_POS])
    return player_ships
