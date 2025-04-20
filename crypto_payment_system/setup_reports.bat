@echo off
echo Setting up daily reports task...

REM Get the current directory
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

REM Create a temporary XML file for the scheduled task
echo ^<?xml version="1.0" encoding="UTF-16"?^> > "%TEMP%\crypto_reports_task.xml"
echo ^<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"^> >> "%TEMP%\crypto_reports_task.xml"
echo   ^<RegistrationInfo^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<Description^>Daily Crypto Payment System Reports^</Description^> >> "%TEMP%\crypto_reports_task.xml"
echo   ^</RegistrationInfo^> >> "%TEMP%\crypto_reports_task.xml"
echo   ^<Triggers^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<CalendarTrigger^> >> "%TEMP%\crypto_reports_task.xml"
echo       ^<StartBoundary^>2023-01-01T00:05:00^</StartBoundary^> >> "%TEMP%\crypto_reports_task.xml"
echo       ^<Enabled^>true^</Enabled^> >> "%TEMP%\crypto_reports_task.xml"
echo       ^<ScheduleByDay^> >> "%TEMP%\crypto_reports_task.xml"
echo         ^<DaysInterval^>1^</DaysInterval^> >> "%TEMP%\crypto_reports_task.xml"
echo       ^</ScheduleByDay^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^</CalendarTrigger^> >> "%TEMP%\crypto_reports_task.xml"
echo   ^</Triggers^> >> "%TEMP%\crypto_reports_task.xml"
echo   ^<Principals^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<Principal id="Author"^> >> "%TEMP%\crypto_reports_task.xml"
echo       ^<LogonType^>InteractiveToken^</LogonType^> >> "%TEMP%\crypto_reports_task.xml"
echo       ^<RunLevel^>LeastPrivilege^</RunLevel^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^</Principal^> >> "%TEMP%\crypto_reports_task.xml"
echo   ^</Principals^> >> "%TEMP%\crypto_reports_task.xml"
echo   ^<Settings^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<MultipleInstancesPolicy^>IgnoreNew^</MultipleInstancesPolicy^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<DisallowStartIfOnBatteries^>false^</DisallowStartIfOnBatteries^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<StopIfGoingOnBatteries^>false^</StopIfGoingOnBatteries^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<AllowHardTerminate^>true^</AllowHardTerminate^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<StartWhenAvailable^>true^</StartWhenAvailable^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<RunOnlyIfNetworkAvailable^>false^</RunOnlyIfNetworkAvailable^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<IdleSettings^> >> "%TEMP%\crypto_reports_task.xml"
echo       ^<StopOnIdleEnd^>true^</StopOnIdleEnd^> >> "%TEMP%\crypto_reports_task.xml"
echo       ^<RestartOnIdle^>false^</RestartOnIdle^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^</IdleSettings^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<AllowStartOnDemand^>true^</AllowStartOnDemand^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<Enabled^>true^</Enabled^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<Hidden^>false^</Hidden^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<RunOnlyIfIdle^>false^</RunOnlyIfIdle^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<WakeToRun^>false^</WakeToRun^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<ExecutionTimeLimit^>PT1H^</ExecutionTimeLimit^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<Priority^>7^</Priority^> >> "%TEMP%\crypto_reports_task.xml"
echo   ^</Settings^> >> "%TEMP%\crypto_reports_task.xml"
echo   ^<Actions Context="Author"^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^<Exec^> >> "%TEMP%\crypto_reports_task.xml"
echo       ^<Command^>python^</Command^> >> "%TEMP%\crypto_reports_task.xml"
echo       ^<Arguments^>%SCRIPT_DIR%\send_reports.py^</Arguments^> >> "%TEMP%\crypto_reports_task.xml"
echo       ^<WorkingDirectory^>%SCRIPT_DIR%^</WorkingDirectory^> >> "%TEMP%\crypto_reports_task.xml"
echo     ^</Exec^> >> "%TEMP%\crypto_reports_task.xml"
echo   ^</Actions^> >> "%TEMP%\crypto_reports_task.xml"
echo ^</Task^> >> "%TEMP%\crypto_reports_task.xml"

REM Register the task
schtasks /create /tn "CryptoPaymentReports" /xml "%TEMP%\crypto_reports_task.xml" /f

if %ERRORLEVEL% EQU 0 (
    echo Task "CryptoPaymentReports" created successfully.
    echo The report will run daily at 00:05 AM.
) else (
    echo Failed to create the task. Please run this script as administrator.
)

REM Clean up the temporary file
del "%TEMP%\crypto_reports_task.xml"

echo.
echo To manually send a report now, run:
echo python %SCRIPT_DIR%\send_reports.py
echo. 