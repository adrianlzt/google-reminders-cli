# google-reminders-cli

This is a simple tool for creating Google reminders from the command line.
The only supported feature is creating a single reminder in a specified time and
date, and is done interactively:

```
$ ./remind
What's the reminder: Pay bills
When do you want to be reminded: tomorrow at 4pm

"Pay bills" on Saturday, 2019-2-16 at 16:00

Do you want to save this? [Y/n] y
Reminder set successfully
```

Or directly:
```
$ ./remind Pay bills tomorrow at 4pm
"Pay bills" on Saturday, 2019-2-16 at 16:00

Do you want to save this? [Y/n] y
Reminder set successfully
```

Run `remind -h` to see additional acceptable time formats

Currently there is no official support for reminders in Google API, so instead, this
tool imitates a browser request.
App API keys are provided in a separate file and you may either use them or change them with
your own keys.

Format of the ~/.config/google-reminders/app_keys.json file that should be created:
```
{
    "APP_CLIENT_ID": "xxx.apps.googleusercontent.com",
    "APP_CLIENT_SECRET": "abcdef"
}
```
