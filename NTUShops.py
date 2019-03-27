from datetime import datetime, date, time, timedelta
import time
import telepot
from telepot.loop import MessageLoop
from bs4 import BeautifulSoup
from urllib.request import urlopen
import csv
import calendar
import sys
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from math import sin, cos, sqrt, atan2, radians

#Global Variable
markup = urlopen("http://www.mom.gov.sg/employment-practices/public-holidays")
soup = BeautifulSoup(markup, "html.parser")
bot = telepot.Bot("367085228:AAELMUAHkek1srx-_QeM0it7-lJ5OkxkSYo")
#These are declared as multiple functions requires them.
tp = ''
a = True
b = False
x,y = 0,0

#Check for public holiday. Return which day of the week with PH being 8
def phcheck():
    #Extract list of PH from MOM website.
    s = soup.findAll('tbody')[1]
    for data in s.stripped_strings:
        data = data.replace('\n',' ')
        #Ignore data if it isn't a date.
        try:
            day = datetime.strptime(data, '%d %B %Y').date()
            if day == (datetime.utcnow() + timedelta(hours=8)).date():
                return 8
            #If PH falls on Sunday, monday will be a PH as well. 
            elif (day == ((datetime.utcnow() + timedelta(hours=8)).date() - timedelta(days = 1)) and day.isoweekday() == 7):
                return 8
        except:
            pass
    return (datetime.utcnow() + timedelta(hours=8)).date().isoweekday()

#Find all shops.
def shops():
    #Open csv file containing all information on shops. UTF8 encoding is not used due to error with SSH.
    file = open('Opening Hours.csv', newline='', encoding='latin-1')
    openinghours = csv.reader(file)
    ls = []
    #Covert csv file into 2d list.
    for row in openinghours:
        ls.append(row)
    #Remove first row of data. Not relavant as first row is description
    ls.pop(0)
    #List is the format: Name, Type, lat, long, opening time(monday), closing time(monday), ..., opening time(public holiday), closing time(public holiday), Address
    return ls

#Return list with updated list with only shop's status  
def ohcheck(ls):
    #utcnow allows bot is be used on servers with different timezone.
    timenow = (datetime.utcnow() + timedelta(hours=8)).time()
    day = phcheck()
    for i in range(len(ls)):
        #Value of 'closed' returns an error.
        try:
            #Shops are opened if they fall between this timing.
            if (timenow >= datetime.strptime(ls[i][2*day+2],"%H:%M").time() and timenow < datetime.strptime(ls[i][2*day+3],"%H:%M").time()):
                ls[i].append("(Opened)")
            #Shops are closed if they fall outside this timing.
            else:
                ls[i].append("(Closed)")
        #Shops are closed if the value retrieved are closed. As they are closed for the entire day.
        except:
            ls[i].append("(Closed)")
    return ls

#Filter list for shops that are opened.
def ohfilter(ls):
    l = []
    ls = ohcheck(ls)
    day = phcheck()
    #Find which column to check for opening hours.
    for i in range(len(ls)):
        #Opening hours are listed in ascending order from ls[i][4:]
        if ls[i][-1] == "(Opened)":
            #Delete all opening hours for days that are not relevant.
            del ls[i][2*day+4:-2]
            del ls[i][4:2*day+2]
            #Only Name, Type, lat, long, Opening Time, Closing Time, Status and Address are lefted in the list.
            l.append(ls[i])
        else:
            pass
    return l

#Filter by type of shops. E.g. Stationaries, Food, Drinks...
def genre(ls, tp):
    l = []
    for i in range(len(ls)):
        if ls[i][1] == tp:
            l.append(ls[i])
    return l

#Calculated current distance to shops and arrange them in ascending order.
def dist(ls,x,y):
    x = radians(x)
    y = radians(y)
    for i in range(len(ls)):
        #Retrieve and removes x,y coords from list.
        x1 = radians(float(ls[i].pop(2)))
        y1 = radians(float(ls[i].pop(2)))
        #Aprroximate radius of the earth in m.
        R = 6371000
        d = sin((x1 - x) / 2)**2 + cos(x) * cos(x1) * sin((y1 - y) / 2)**2
        c = 2 * atan2(sqrt(d), sqrt(1 - d))
        #Add the distance of each shop to the back of the list for sorting.
        ls[i].append(R*c)
    ls = sorted(ls, key = lambda x:x[-1])
    #Add distance to status.
    for i in range(len(ls)):
        dist = str(round(ls[i].pop(),2))
        ls[i][-2] = ls[i][-2] + '\nAprroximate Distance: ' + dist + 'm'
    return ls

#Search for a specific shop.
def details(name):
    ls = shops()
    ls = ohcheck(ls)
    for i in range(len(ls)):
        #Return the shop that user is searching for.
        if name.lower().replace(' ','') == ls[i][0].lower().replace(' ',''):
            #Delete coordinates as they are not needed.
            del ls[i][2:4]
            return ls[i]
    return False

#Craft a message with ALL operating hours. 
def sendfullmsg(ls,chat_id):
    #Name, Status, Type, Address
    smsg = ls.pop(0) + ' ' + ls.pop() + '\nType: ' +ls.pop(0) + '\n' + ls.pop()
    #Check if distance is still in the list.
    if (len(ls) != 2 and len(ls) != 16):
        del ls[0:2]
    #Message cannot be longer than 200 characters.
    bot.sendMessage(chat_id, smsg)
    smsg = 'Opening Hours:'
    for i in range(int(len(ls)/2)):
        #Last pair is for public holidays.
        if i == 7:
            if str(ls[0]).title() != 'Closed':
                smsg += '\nPublic Holidays: ' + ls.pop(0) + ' - ' + ls.pop(0)
            elif str(ls[0]).title() != 'Closed':
                smsg += '\nPublic Holidays: Closed'
            break
        smsg += '\n' + calendar.day_name[i] + ': ' + ls.pop(0) + ' - ' + ls.pop(0)
    bot.sendMessage(chat_id, smsg)
    return

#Craft a message with ONLY today's operating hours.
def sendmsg(ls,chat_id):
    #Name, Status, Type, Address
    smsg = ls.pop(0) + ' ' + ls.pop() + '\nType: ' + ls.pop(0) + '\n' + ls.pop() + '\nOpening Hours: '
    #Check if distance is still in the list.
    if len(ls) != 2:
        del ls[0:2]
    if ls[0].lower() == "closed":
            smsg += 'Closed'
    else:
        smsg += ls.pop(0) + ' - ' + ls.pop(0) + '\n'
    bot.sendMessage(chat_id, smsg)
    return

#Shops that are opened will be placed at the top. Then sorted by name.
def ohstatus(ls):
    ls = sorted(sorted(ls, key = lambda x : x[0]), key = lambda x : x[-1], reverse = True)
    return ls

#Search for type of shops. a: Sort by distance b: Filter if shop is opened
def fullresp(a,b,tp,x,y,chat_id):
    ls = shops()
    ls = genre(ls, tp)
    if b == 'Yes':
            ls = ohfilter(ls)
    if b == 'No':
            ls = ohcheck(ls)
    if a == 'Yes':
            ls = dist(ls,x,y)
    if a == 'No':
            ls = ohstatus(ls)
    #For multiple shops found. Send message individually due to maximum length of message.
    for i in range(len(ls)):
        sendmsg(ls[i],chat_id)
    #List is empty.
    if len(ls) == 0:
        bot.sendMessage(chat_id,'No shops are found. Sorry! :(')
    return

#Generate inlinekeyboard. Codes do not need to be update even if list changes.
def kbgenerator(tp):
    #UTF8 encoding is not used due to error with SSH.
    file = open('Opening Hours.csv', newline='', encoding='latin-1')
    openinghours = csv.reader(file)
    ls = []
    kb = []
    for row in openinghours:
        ls.append(row)
    #Find which column to keep.
    col = ls[0].index(tp)
    del ls[0]
    #Removes duplicates and header.
    ls = list(set([i[col] for i in ls]))
    for i in range(len(ls)):        
        kb.append([InlineKeyboardButton(text=ls[i], callback_data=(ls[i]+' '+tp))])
    return kb

#Catch response from online keyboard
def on_callback_query(msg):
    query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
    #Function that only searches for one shop. Function ends here.
    if query_data.rsplit(' ', 1)[-1] == 'Name':
        sendfullmsg(details(query_data.rsplit(' ', 1)[0]),from_id)
        return
    #Processing all neccessary information and storing them in global variables.
    elif query_data.rsplit(' ', 1)[-1] == 'Type':
        #query_data is split into 2 words. Only interested in the one on the left.
        global tp
        tp = query_data.rsplit(' ', 1)[0]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Yes', callback_data='Yes Operating')],
            [InlineKeyboardButton(text='No', callback_data='No Operating')]
            ])
        bot.sendMessage(from_id, 'Do you need it to be opened now?', reply_markup=keyboard)
    elif query_data.rsplit(' ', 1)[-1] == 'Operating':
        global b
        b = query_data.rsplit(' ', 1)[0]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Yes', callback_data='Yes Location')],
            [InlineKeyboardButton(text='No', callback_data='No Location')],
            ])
        bot.sendMessage(from_id, 'Sort by distance?', reply_markup=keyboard)
    elif query_data.rsplit(' ', 1)[-1] == 'Location':
        global a
        a  = query_data.rsplit(' ', 1)[0]
        if a == 'Yes':
            bot.sendMessage(from_id, 'Please send us your current location.',
                reply_markup=ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="Send location now.",request_location=True)]
                ],one_time_keyboard=True,resize_keyboard=True))
        else:
            #x & y are 0 as this function is called only when user not interested in distance.
            fullresp(a,b,tp,0,0,from_id)

#Handles keyboard messages.    
def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    #Other if statements is not able to handle 'location' input. Return is needed and placed at the top.
    if content_type == 'location':
        x = msg['location']['latitude']
        y = msg['location']['longitude']
        #All other variables have already been input. Location is the last. Can call for function.
        fullresp(a,b,tp,x,y,chat_id)
        return
    if (msg['text'] != "Details of a single shop." and msg['text'] != "Type of shops"):
        bot.sendMessage(chat_id, 'What are you searching for?',
            reply_markup=ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="Details of a single shop."),
             KeyboardButton(text="Type of shops.")]],resize_keyboard=True))
    if msg['text'] == "Details of a single shop.":
        kb = kbgenerator('Name')
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
        bot.sendMessage(chat_id, 'What is the name of the shop?', reply_markup=keyboard)
    if msg['text'] == "Type of shops.":
        kb = kbgenerator('Type')
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
        bot.sendMessage(chat_id, 'What type of shops are you looking for?', reply_markup=keyboard)
        
#Text messages goes to handle. Inline keyboard replies goes to on_callback_query.
MessageLoop(bot,{'chat': handle,'callback_query': on_callback_query}).run_as_thread()
print('Listening ...')

while 1:
    time.sleep(10)
