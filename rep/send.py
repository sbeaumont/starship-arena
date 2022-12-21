import os
import sys
from collections import defaultdict
import fnmatch
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

SHIP_NAME_POS = 0
PLAYER_NAME_POS = 4

# Email config file is expected:
# (sender email)
# (app password)
# and then further lines:
# (Player name) (Email)


def send_email(email_cfg: str, game_dir: str, result_file: str, name: str):
    with open(email_cfg) as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        email_sender = lines[0]
        email_password = lines[1]
        player_emails = {name: email for name, email in [line.split() for line in lines[2:]]}

    if name not in player_emails:
        sys.exit(f"Player {name} not found in email list to send {result_file}.")
    email_receiver = player_emails[name]

    print(f"Sending {result_file} to {name} email {email_receiver}")

    msg_content = """Here's your result file!"""
    body = MIMEText(msg_content, 'html')

    em = MIMEMultipart('mixed')
    em['From'] = email_sender
    em['To'] = player_emails[name]
    em['Subject'] = f"[Space Arena] Game {game_dir} Result {result_file}"
    em.attach(body)

    with open(os.path.join(game_dir, result_file), "rb") as attachment:
        p = MIMEApplication(attachment.read(), _subtype="pdf")
        p.add_header('Content-Disposition', f"attachment; filename={result_file}")
        em.attach(p)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(email_sender, email_password)
        smtp.sendmail(email_sender, email_receiver, em.as_string())


def send_results_for_round(game_directory: str, init_file_name: str, email_config_file_name: str, round_number: int):
    if not os.path.exists(game_directory):
        sys.exit(f"{game_directory} not found.")
    init_file = os.path.join(game_directory, init_file_name)
    if not os.path.exists(init_file):
        sys.exit(f"{init_file} not found.")
    if not os.path.exists(email_config_file_name):
        sys.exit(f"{email_config_file_name} not found.")

    player_ships = defaultdict(list)
    with open(os.path.join(game_directory, init_file_name)) as f:
        lines = [line.strip().split(' ') for line in f.readlines() if line.strip()]
        for line in lines:
            player_ships[line[PLAYER_NAME_POS]].append(line[SHIP_NAME_POS])

    gamedir_contents = os.listdir(game_directory)
    for name, ship_names in player_ships.items():
        for ship_name in ship_names:
            results = fnmatch.filter(gamedir_contents, f"{ship_name}*{round_number}.pdf")
            if len(results) > 1:
                sys.exit(f"Got multiple results for {ship_name} in round {round_number}: {results}")
            send_email(email_config_file_name, game_directory, results[0], name)


