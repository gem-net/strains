from collections import defaultdict, OrderedDict
from datetime import datetime
from threading import Thread

from flask import current_app, render_template, url_for
from flask_mail import Message
import gspread
from oauth2client.service_account import ServiceAccountCredentials


from oauth import mail


EMAIL_DICT = defaultdict(list)


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(subject, recipients, text_body, html_body,
               attachments=None, sender=None,
               sync=False):
    if sender is None:
        sender = current_app.config['MAIL_SENDER']
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    if attachments:
        for attachment in attachments:
            msg.attach(*attachment)
    if sync:
        mail.send(msg)
    else:
        Thread(target=send_async_email,
               args=(current_app._get_current_object(), msg)).start()


def notify_lab(rq):
    """Send notification email to lab handling strain."""
    lab_emails = EMAIL_DICT[rq.strain_lab]
    requester_name = rq.requester.display_name
    strain = rq.strain
    subject = "[Strains] New REQUEST from {}: {}".format(requester_name, strain.plasmid)
    text_body = render_template('email/new_request.txt', rq=rq)
    html_body = render_template('email/new_request.html', rq=rq)
    send_email(subject,
               recipients=lab_emails,
               text_body=text_body, html_body=html_body)


def email_comment(comment):
    """Send new comment notification.

    If commenter is requester, either 1) email volunteer if exists or
    2) email lab emails.

    If commenter is shipper, email requester.

    If commenter is not shipper or requester, either 1) email requester
    and shipper if shipper exists, or 2) email requester and lab emails.
    """
    rq = comment.request
    commenter = comment.commenter
    requester = comment.request.requester
    shipper = comment.request.shipper

    lab_emails = EMAIL_DICT[rq.strain_lab]
    recipients = []
    if commenter == requester:
        if shipper:
            recipients.append(shipper.email)
        else:
            recipients.extend(lab_emails)
    if commenter == shipper:
        recipients.append(requester.email)
    if commenter not in (shipper, requester):
        recipients.append(requester.email)
        if shipper:
            recipients.append(shipper.email)
        else:
            recipients.extend(lab_emails)

    subject = "[Strains] New COMMENT from {} on request {}".format(commenter.display_name, rq.id)
    text_body = render_template('email/new_comment.txt', rq=rq, comment=comment)
    html_body = render_template('email/new_comment.html', rq=rq, comment=comment)
    send_email(subject,
               recipients=recipients,
               text_body=text_body, html_body=html_body)


def email_new_status(rq, user):
    """Send new status notification, including user that modified status.

    If user is requester, either 1) email volunteer if exists or
    2) email lab emails.

    If user is shipper, email requester.

    If user is not shipper or requester, either 1) email requester
    and shipper if shipper exists, or 2) email requester and lab emails.
    """

    requester = rq.requester
    shipper = rq.shipper

    lab_emails = EMAIL_DICT[rq.strain_lab]
    recipients = []
    if user == requester:
        if shipper:
            recipients.append(shipper.email)
        else:
            recipients.extend(lab_emails)
    if user == shipper:
        recipients.append(requester.email)
    if user not in (shipper, requester):
        recipients.append(requester.email)
        if shipper:
            recipients.append(shipper.email)
        else:
            recipients.extend(lab_emails)
    time = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    subject = "[Strains] New STATUS on request {}".format(rq.id)
    text_body = render_template('email/new_status.txt', rq=rq, user=user, time=time)
    html_body = render_template('email/new_status.html', rq=rq, user=user, time=time)
    send_email(subject,
               recipients=recipients,
               text_body=text_body, html_body=html_body)


def email_new_volunteer(rq):
    """Send new volunteer notification to requester."""
    time = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    subject = "[Strains] Your request has been accepted."
    text_body = render_template('email/new_shipper.txt', rq=rq, time=time)
    html_body = render_template('email/new_shipper.html', rq=rq, time=time)
    send_email(subject, recipients=[rq.requester.email],
               text_body=text_body, html_body=html_body)


def get_gsheet_dict():
    """Get dictionary of sheet_name: sheet object."""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        current_app.config['CREDS_JSON'], scope)

    gc = gspread.authorize(credentials)
    # display('List spreadsheet files:', gc.list_spreadsheet_files())
    file = gc.open("C-GEM strains list")
    wsheets = file.worksheets()
    sheet_dict = OrderedDict([(i.title, i) for i in wsheets])
    return sheet_dict


def load_lab_emails():
    """Load emails from google sheet into global EMAIL_DICT."""
    global EMAIL_DICT
    sheet_dict = get_gsheet_dict()

    emails = sheet_dict['Emails']
    email_rows = emails.get_all_values()[1:]

    for lab, email, *_ in email_rows:
        EMAIL_DICT[lab].append(email)
    print('Loaded lab emails.')
