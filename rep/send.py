import os
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

SHIP_NAME_POS = 0
PLAYER_NAME_POS = 4

# Email config file is expected:
# (sender email)
# (app password)
# and then further lines:
# (Player name) (Email)


def send_email(email_cfg: str, game_dir: str, result_file: str, name: str, ship_name: str, round_number: int, send_manual: bool):
    email_password, email_sender, player_emails = load_email_config(game_dir, email_cfg)

    if name not in player_emails:
        sys.exit(f"Player {name} not found in email list to send {result_file}.")
    email_receiver = player_emails[name]

    print(f"Sending {result_file} to {name} email {email_receiver}")

    em = MIMEMultipart('mixed')
    em['From'] = email_sender
    em['To'] = player_emails[name]
    em['Subject'] = f"[Space Arena] {game_dir}/{result_file}"

    # Email Body
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(ROUND_EMAIL_TEMPLATE)

    template_data = {
        "name": name,
        "round_nr": str(round_number),
        "next_round_deadline": 'TBD'
    }

    body = MIMEText(template.render(template_data), 'html')
    em.attach(body)

    # Attachment: Report PDF
    with open(os.path.join(game_dir, result_file), "rb") as attachment:
        p = MIMEApplication(attachment.read(), _subtype="pdf")
        p.add_header('Content-Disposition', "attachment", filename=result_file)
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


def load_email_config(game_directory, email_cfg):
    with open(os.path.join(game_directory, email_cfg)) as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        email_sender = lines[0]
        email_password = lines[1]
        player_emails = {name: email for name, email in [line.split() for line in lines[2:]]}
    return email_password, email_sender, player_emails


def check_ok_to_send(email_config_file_name, game_directory, init_file_name):
    # Check if all is okay
    if not os.path.exists(game_directory):
        sys.exit(f"{game_directory} not found.")
    init_file = os.path.join(game_directory, init_file_name)
    if not os.path.exists(init_file):
        sys.exit(f"{init_file} not found.")
    if not os.path.exists(os.path.join(game_directory, email_config_file_name)):
        sys.exit(f"{os.path.join(game_directory, email_config_file_name)} not found.")

    player_emails = load_email_config(game_directory, email_config_file_name)[2]
    player_ships = load_init_file(game_directory, init_file_name)
    emails_not_present = list()
    for player_name in player_ships.keys():
        if player_name not in player_emails:
            emails_not_present.append(player_name)
    if len(emails_not_present) > 0:
        sys.exit(f"Player(s) {''.join(emails_not_present)} email address not found in email config file.")


def send_results_for_round(game_directory: str, init_file_name: str, email_config_file_name: str, round_number: int, include_manual: bool):
    check_ok_to_send(email_config_file_name, game_directory, init_file_name)
    player_ships = load_init_file(game_directory, init_file_name)

    # For each player, for each ship, send one email
    round_name = f"round-{round_number}"
    round_dir = os.path.join(game_directory, round_name)
    round_contents = os.listdir(round_dir)
    for name, ship_names in player_ships.items():
        for ship_name in ship_names:
            results = fnmatch.filter(round_contents, f"{ship_name}-{round_name}.pdf")
            if len(results) > 1:
                sys.exit(f"Got multiple results for {ship_name} in round {round_number}: {results}")
            elif len(results) == 1:
                send_email(email_config_file_name, round_dir, results[0], name, ship_name, round_number, include_manual)


def load_init_file(game_directory, init_file_name):
    # Collect ships per player
    player_ships = defaultdict(list)
    with open(os.path.join(game_directory, init_file_name)) as f:
        lines = [line.strip().split(' ') for line in f.readlines() if line.strip()]
        for line in lines:
            player_ships[line[PLAYER_NAME_POS]].append(line[SHIP_NAME_POS])
    return player_ships
