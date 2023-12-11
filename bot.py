# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from langchain.llms import AzureOpenAI
# from langchain.embeddings import OpenAIEmbeddings
# from langchain.chat_models.azure_openai import AzureChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from llm_backend import pdf_query_updated
import os
from datetime import datetime

# os.environ["OPENAI_API_TYPE"] = "azure"
# os.environ["OPENAI_API_BASE"] = "https://utterancesresource.openai.azure.com/"
# os.environ["OPENAI_API_KEY"] = "5ea3e8e59b8a418e9cc3c066f853b0c0"
# os.environ["OPENAI_API_VERSION"] = "2023-07-01-preview"

os.environ["OPENAI_API_KEY"]= 'e63ed695495543d58595fab4e27e4ff1'
os.environ['OPENAI_API_VERSION'] = '2023-07-01-preview'
os.environ['OPENAI_API_BASE'] = 'https://tv-llm-applications.openai.azure.com/'
os.environ['OPENAI_API_TYPE'] = 'azure'

from botbuilder.core import ActivityHandler, MessageFactory, TurnContext,CardFactory
from botbuilder.schema import ChannelAccount, CardAction, ActionTypes, SuggestedActions,HeroCard,  CardAction
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.questionanswering import QuestionAnsweringClient
from azure.ai.language.conversations import ConversationAnalysisClient
import pyodbc
import pandas as pd
from botbuilder.core import CardFactory


# from botbuilder.core import (
#     MessageFactory,
#     TurnContext,
#     CardFactory,
# )
# from botbuilder.dialogs import (
#     ComponentDialog,
#     WaterfallDialog,
#     DialogTurnResult,
#     WaterfallStepContext,
# )
# from botbuilder.dialogs.prompts import TextPrompt
# from botbuilder.core import ActionTypesResult





# Azure QnA Maker configuration
endpoint = "https://conversationallanguageunderstanding.cognitiveservices.azure.com/"
credential = AzureKeyCredential("1c7bdfbc42714f2bb62c12ccc6fe1220")
knowledge_base_project = "Guardsman-QandA"
deployment = "production"

# CLU configuration
clu_endpoint = "https://conversationallanguageunderstanding.cognitiveservices.azure.com/"
clu_key = "1c7bdfbc42714f2bb62c12ccc6fe1220"
clu_project_name = "Guardsman"
clu_deployment_name = "Guardsman_deployment"

def separate_outputs_from_db(results):
          
    ex_date = results[0][1]
    ex_day = results[0][2]
    start_time = format_time(results[0][3])
    end_time = format_time(results[0][4])
    return [ex_date,ex_day,start_time,end_time]

def format_time(time_string):
    # Define the input time format with an optional fractional part
    input_formats = ["%H:%M:%S.%f", "%H:%M:%S"]

    for format_string in input_formats:
        try:
            # Try to convert the string to datetime using the current format
            time_datetime = datetime.strptime(time_string, format_string)

            # If successful, format and return the result
            formatted_time = time_datetime.strftime("%I:%M %p")
            return formatted_time

        except ValueError:
            pass  # Ignore errors and try the next format

    # If none of the formats work, raise an error
    raise ValueError("Invalid time string format: {}".format(time_string))

def convert_dates(results):
    converted_results = []

    for result in results:
        name, date_str, day, start_time_str, end_time_str = result

        # Convert date string to datetime
        date_datetime = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Convert start and end times
        start_time_formatted = format_time(start_time_str[:7])
        end_time_formatted = format_time(end_time_str[:7])

        converted_results.append((name, date_datetime, day, start_time_formatted, end_time_formatted))

    return converted_results

# Function to get answers from QnA Maker
def custom_QandA(question_from_user):
    client = QuestionAnsweringClient(endpoint, credential)
    with client:
        # Use the provided question_from_user parameter
        question = question_from_user
        # Get answers from QnA Maker
        output = client.get_answers(
            question=question,
            project_name=knowledge_base_project,
            deployment_name=deployment
        )
        # Return the first answer
        return output.answers[0]

client = ConversationAnalysisClient(clu_endpoint, AzureKeyCredential(clu_key))

def answers_from_clu(question_from_user):
    client = ConversationAnalysisClient(clu_endpoint, AzureKeyCredential(clu_key))
    with client:
        result = client.analyze_conversation(
            task={
                "kind": "Conversation",
                "analysisInput": {
                    "conversationItem": {
                        "participantId": "1",
                        "id": "1",
                        "modality": "text",
                        "language": "en",
                        "text": question_from_user
                    },
                    "isLoggingEnabled": False
                },
                "parameters": {
                    "projectName": clu_project_name,
                    "deploymentName": clu_deployment_name,
                    "verbose": True
                }
            }
        )
    return result    


def get_connection_string():
#     conn_string = ("Driver={SQL Server};"
#                    "Server=TL166;"
#                    "Database=GMBOT;"
#                    "Trusted_Connection=yes;")
    
    conn_string = ('Driver={ODBC Driver 18 for SQL Server};'
                   'Server=tcp:mysqlserver1666.database.windows.net,1433;'
                   'Database=GMBOT;'
                   'Uid=azureuser;'
                   'Pwd={Azure@23498};')
    return conn_string

def clu_get_intent(result_from_clu):
    top_intent = result_from_clu["result"]["prediction"]["topIntent"]
    intents_df = pd.DataFrame(result_from_clu["result"]["prediction"]["intents"])
    confidence_top_intent = intents_df[intents_df.category == top_intent].confidenceScore
    return top_intent, confidence_top_intent

username = 'Thomas'
date = "2023-11-13"

class MyBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        question = turn_context.activity.text
        answer = custom_QandA(question)
        custom_QandA_Confidence = answer.confidence
        lower_question = question.lower()
        print(f'Debug: {custom_QandA_Confidence}')
        if custom_QandA_Confidence > 0.7:
            # Check for specific user input to provide suggested actions
            if "about organization" in lower_question:
                org_available_actions = SuggestedActions(
                    actions=[
                        CardAction(title="Services", type=ActionTypes.im_back, value="Services"),
                        CardAction(title="Contact us", type=ActionTypes.im_back, value="Contact us"),
                        CardAction(title="Locations", type=ActionTypes.im_back, value="Locations"),
                        CardAction(title="Clients", type=ActionTypes.im_back, value="Clients")
                    ]
                )
                aboutorganization_response_activity = MessageFactory.text("What else would you like to know about Guardsman?")
                aboutorganization_response_activity.suggested_actions = org_available_actions
                await turn_context.send_activity(answer.answer)
                await turn_context.send_activity(aboutorganization_response_activity)

                

            # elif "services" in lower_question:
            #     services_available_actions = SuggestedActions(
            #         actions=[
            #             CardAction(title="Manned Guarding", type=ActionTypes.im_back, value="Manned Guarding"),
            #             CardAction(title="Temporary Staff Support Services", type=ActionTypes.im_back, value="Temporary Staff Support Services"),
            #             CardAction(title="Commercial Cleaning", type=ActionTypes.im_back, value="Commercial Cleaning"),
            #             CardAction(title="CCTV Towers", type=ActionTypes.im_back, value="CCTV Towers"),
            #             CardAction(title="Car Parking Management", type=ActionTypes.im_back, value="Car Parking Management")
            #         ]
            #     )
            #     services_response_activity = MessageFactory.text("Kindly select the service name to access detailed information")
            #     services_response_activity.suggested_actions = services_available_actions
            #     await turn_context.send_activity(services_response_activity)

            elif "leave policies" in lower_question:
                LP_actions = SuggestedActions(
                    actions=[                    
                        CardAction(title="Vacation Leave", type=ActionTypes.im_back, value="Vacation Leave"),
                        CardAction(title="Sick Leave", type=ActionTypes.im_back, value="Sick Leave"),
                        CardAction(title="Service Incentive Leave", type=ActionTypes.im_back,
                                    value="Service Incentive Leave"),
                        CardAction(title="Paternity Leave", type=ActionTypes.im_back, value="Paternity Leave"),
                    ]
                )
                Lp_response_activity = MessageFactory.text('Kindly choose the category of leave policy information you are seeking:')
                Lp_response_activity.suggested_actions = LP_actions
                await turn_context.send_activity(Lp_response_activity)
                
                
            elif  "leave management" in lower_question:
                    LM_actions = SuggestedActions(
                    actions=[
                        CardAction(title="Check My Leave Balances", type=ActionTypes.im_back, value="Check My Leave Balances"),
                        CardAction(title="Apply Leave", type=ActionTypes.im_back, value="Apply Leave"),
                        CardAction(title="Leave Policies", type=ActionTypes.im_back, value="Leave Policies")
                    ]
                )
                    LM_response_activity = MessageFactory.text("How may I assist you with your leave management needs?")
                    LM_response_activity.suggested_actions = LM_actions
                    await turn_context.send_activity(LM_response_activity)

            elif "payroll details" in lower_question:
                payroll_available_actions = SuggestedActions(
                    actions=[
                        CardAction(title="Pay Slips", type=ActionTypes.im_back, value="Pay Slips"),
                        CardAction(title="Payroll Info", type=ActionTypes.im_back, value="Payroll Info")
                    ]
                )
                payroll_response_activity = MessageFactory.text("Would you prefer to inquire about comprehensive payroll details or access your recent payslips?")
                payroll_response_activity.suggested_actions = payroll_available_actions
                await turn_context.send_activity(payroll_response_activity)

            elif 'yes' in lower_question:
                yes_suggested_actions = SuggestedActions(
                    actions=[
                        CardAction(title="Leave Management", type=ActionTypes.im_back, value="Leave Management"),
                        CardAction(title="Get Working Hours", type=ActionTypes.im_back, value="Get Working Hours"),
                        CardAction(title="Payroll Details", type=ActionTypes.im_back, value="Payroll Details"),
                        CardAction(title="About Organization", type=ActionTypes.im_back, value="About Organization")
                    ]
                )
                yes_response_activity = MessageFactory.text("What else can I assist you with?")
                yes_response_activity.suggested_actions = yes_suggested_actions
                await turn_context.send_activity(yes_response_activity)

            
            elif 'no' in lower_question:
                 await turn_context.send_activity(answer.answer)

            elif 'thankyou' in lower_question:
                await turn_context.send_activity(answer.answer)

            
            elif 'hi' in lower_question:
                hi_suggested_actions = SuggestedActions(
                    actions=[
                        CardAction(title="Leave Management", type=ActionTypes.im_back, value="Leave Management"),
                        CardAction(title="Get Working Hours", type=ActionTypes.im_back, value="Get Working Hours"),
                        CardAction(title="Payroll Details", type=ActionTypes.im_back, value="Payroll Details"),
                        CardAction(title="About Organization", type=ActionTypes.im_back, value="About Organization")
                    ]
                )
                hi_response_activity = MessageFactory.text("What else can I assist you with?")
                hi_response_activity.suggested_actions = hi_suggested_actions
                await turn_context.send_activity(hi_response_activity)

            # elif 'get working hours' in lower_question:
            #     GWH_available_actions = SuggestedActions(
            #         actions=[
            #             CardAction(title="Last Week Working  Hours", type=ActionTypes.im_back, value="Last Week Working  Hours"),
            #             CardAction(title="Next Week Working Hours", type=ActionTypes.im_back, value="Next Week Working Hours")
            #         ]
            #     )
            #     GWH_response_activity = MessageFactory.text("Please choose from available options")
            #     GWH_response_activity.suggested_actions = GWH_available_actions
            #     await turn_context.send_activity(GWH_response_activity)

           

            else:
            #     # Send the answer back to the user
            #     print('Debug1: Unkown Intent')
            #     file_path = r"Guardsman Group FAQ.docx"
            #     query_options = [file_path]
            #     human_query = question
            #     text_splitter=RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
            #     llm = AzureOpenAI(deployment_name='gpt-0301', temperature = 0)
            #     memory = ConversationBufferMemory(memory_key="chat_history", input_key = 'human_input')
 
            #     response,_ = pdf_query_updated(query = human_query, text_splitter = text_splitter, llm = llm, query_options = query_options, memory = memory)
 
            #     response_activity = MessageFactory.text(response)
       
            #     await turn_context.send_activity(response_activity)      
                print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&& \n\n',type(answer.answer))

                if answer.answer == "Thank you for engaging with me; if you ever seek more information or have additional queries, feel free to reach out. To explore further details or initiate a conversation, simply press 'hi,' and I'll be ready to assist you with any inquiries you may have. Goodbye for now, and have a wonderful day!":
                    await turn_context.send_activity(answer.answer)
                else:

                    await turn_context.send_activity(answer.answer)

                    # Provide follow-up suggested actions
                    follow_up_actions = SuggestedActions(
                        actions=[
                            CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                            CardAction(title="No", type=ActionTypes.im_back, value="No"),
                            # Add more follow-up actions as needed
                        ]
                    )
                    follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                    follow_up_response.suggested_actions = follow_up_actions
                    await turn_context.send_activity(follow_up_response)

        else:
            # Handling intents from CLU
            output_from_clu = answers_from_clu(question)
            best_intent, confidence_best_intent = clu_get_intent(output_from_clu)
            print(f'**************** \n\n Debug: \n\n Best Intent - {best_intent} \n\n Confidence - {confidence_best_intent[0]} \n\n****************')
 
            if confidence_best_intent.values[0] > 0.6:

                if best_intent == "GetPaySlip":
                    conn_string = get_connection_string()
                    sql_connection = pyodbc.connect(conn_string)
                    sql_cursor = sql_connection.cursor()
 
                    pay_slips_query = 'SELECT * FROM payslips WHERE EmployeeName = ?;'
                    sql_cursor.execute(pay_slips_query, username)
                    payslip_data = sql_cursor.fetchone()
                    response_activity = MessageFactory.text(f'Your current payslip is:')
                    # await turn_context.send_activity(response_activity)
                    if payslip_data:
                        # Assuming the columns in payslips table are in the order of: EmployeeName, Salary, Deductions, NetPay
                        employeename,employeeid ,salary, deductions, net_pay = payslip_data

                        # Create a Hero Card to display payslip information
                        payslip_hero_card = HeroCard(
                                                    title="Payslip",
                                                    text=(
                                                        f"**Employee:** {employeename}\n\n "
                                                        f"**EmployeeID:** {employeeid}\n\n "
                                                        f"**Salary:** {salary}\n\n"
                                                        f"**Deductions:** {deductions}\n\n"
                                                        f"**Net Pay:** {net_pay}"
                                                    ))


                        # Send the Hero Card as an attachment
                        response_activity = MessageFactory.attachment(CardFactory.hero_card(payslip_hero_card))
                        await turn_context.send_activity(response_activity)
                        follow_up_actions = SuggestedActions(
                            actions=[
                                CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                                CardAction(title="No", type=ActionTypes.im_back, value="No"),
                                # Add more follow-up actions as needed
                            ]
                        )
                        follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                        follow_up_response.suggested_actions = follow_up_actions
                        await turn_context.send_activity(follow_up_response)
                    else:
                        response_activity = MessageFactory.text("No payslip found for the specified user.")
                        await turn_context.send_activity(response_activity)
                        follow_up_actions = SuggestedActions(
                            actions=[
                                CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                                CardAction(title="No", type=ActionTypes.im_back, value="No"),
                                # Add more follow-up actions as needed
                            ]
                        )
                        follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                        follow_up_response.suggested_actions = follow_up_actions
                        await turn_context.send_activity(follow_up_response)

                # elif best_intent == "LeaveManagement":
                #     LM_actions = SuggestedActions(
                #     actions=[
                #         CardAction(title="Check Leave Balances", type=ActionTypes.im_back, value="Check Leave Balances"),
                #         CardAction(title="Apply Leave", type=ActionTypes.im_back, value="Apply Leave"),
                #         CardAction(title="Leave Policies", type=ActionTypes.im_back, value="Leave Policies")
                #     ]
                # )
                #     LM_response_activity = MessageFactory.text("How may I assist you with your leave management needs?")
                #     LM_response_activity.suggested_actions = LM_actions
                #     await turn_context.send_activity(LM_response_activity)


                
                elif best_intent == "CheckLeaveBalances":
                    conn_string = get_connection_string()
                    sql_connection = pyodbc.connect(conn_string)
                    sql_cursor = sql_connection.cursor()
 
                    EL_query = 'SELECT * FROM EmployeeLeave WHERE EmployeeName = ?;'
                    sql_cursor.execute(EL_query, username)
                    EL_data = sql_cursor.fetchone()
                    response_activity = MessageFactory.text(f'Your current Leave balanaces and upcoming leaves are:')
                    # await turn_context.send_activity(response_activity)
                    if EL_data:
                        # Assuming the columns in payslips table are in the order of: EmployeeName, Salary, Deductions, NetPay
                        employeename,employeeid ,SickLeave, PrivilegeLeave,  PaternityLeave,UpcomingThreeLeaves,  Year = EL_data

                        # Create a Hero Card to display payslip information
                        EL_hero_card = HeroCard(
                                        title="Leave Balances and Upcoming Leaves",
                                        text=(
                                            f"**Employee:** {employeename}\n\n"
                                            f"**EmployeeID:** {employeeid}\n\n"
                                            f"**SickLeave:** {SickLeave}\n\n"
                                            f"**PrivilegeLeave:** {PrivilegeLeave}\n\n"
                                            f"**PaternityLeave:** {PaternityLeave}\n\n"
                                            f"**UpcomingThreeLeaves:** {UpcomingThreeLeaves}\n\n"
                                            f"**Year:** {Year}"
                                        )
                                    )


                        # Send the Hero Card as an attachment
                        response_activity = MessageFactory.attachment(CardFactory.hero_card(EL_hero_card))
                        await turn_context.send_activity(response_activity)
                        follow_up_actions = SuggestedActions(
                            actions=[
                                CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                                CardAction(title="No", type=ActionTypes.im_back, value="No"),
                                # Add more follow-up actions as needed
                            ]
                        )
                        follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                        follow_up_response.suggested_actions = follow_up_actions
                        await turn_context.send_activity(follow_up_response)

                elif best_intent == 'ApplyLeave':
                    print(f'Debug: Best Intent - {best_intent}, \n\n Confidence - {confidence_best_intent}')
                    apply_leave_info = "Enter the type of leave required: \n\n  Enter Start Date: \n\n Enter End Date: \n\n\n\n Thank you for the update. Approval for leave requests is subject to manager authorization. Kindly monitor your email for the status of your leave request."
                    AL_response_activity = MessageFactory.text(apply_leave_info)
                    await turn_context.send_activity(AL_response_activity)
                    follow_up_actions = SuggestedActions(
                        actions=[
                            CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                            CardAction(title="No", type=ActionTypes.im_back, value="No"),
                            # Add more follow-up actions as needed
                        ]
                    )
                    follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                    follow_up_response.suggested_actions = follow_up_actions
                    await turn_context.send_activity(follow_up_response)

                elif best_intent == "GetWorkingHours":
                    response = output_from_clu["result"]["prediction"]  

                    entity = response['entities']
                    if len(entity) == 0: 
                        

                        # print('-'*111)
                        # print(entity)
                        # print('-'*111)

                        GWH_available_actions = SuggestedActions(
                        actions=[
                            CardAction(title="Last Week Working  Hours", type=ActionTypes.im_back, value="Last Week Working  Hours"),
                            CardAction(title="Next Week Working Hours", type=ActionTypes.im_back, value="Next Week Working Hours")
                        ]
                    )
                        GWH_response_activity = MessageFactory.text("Please choose from available options")
                        GWH_response_activity.suggested_actions = GWH_available_actions
                        await turn_context.send_activity(GWH_response_activity)
                    

                # elif best_intent == "WorkingHours":
                    
                    else: 
                            
                        response = output_from_clu["result"]["prediction"]  
                        # print('-'*111)
                        # print(response)
                        # print('-'*111)
                        # print(response['entities'][0]['category'])
                        # print('-'*111)
                        entity = response['entities'][0]['category']
                        conn_string = get_connection_string()
                        sql_connection = pyodbc.connect(conn_string)
                        sql_cursor = sql_connection.cursor()

                        if entity == 'PreviousWeek':
                            prev_week_query = "SELECT EmployeeName, Date, Day, ActualStartTime, ActualEndTime FROM EmployeeSchedule WHERE ActualStartTime IS NOT NULL AND EmployeeName = ?;"
                            sql_cursor.execute(prev_week_query, username)
                            prev_week_data = sql_cursor.fetchall()

                            response_activity = MessageFactory.text(f'Your Last Week working Hours info:')
                            print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^', list(prev_week_data))

                            output_prev_week = convert_dates(prev_week_data)
                    
                            data_for_adaptive_card = [
                                {
                                    # "EmployeeName": row[0],
                                    "Date": str(row[1]),
                                    "Day": row[2],
                                    "ActualStartTime": row[3],
                                    "ActualEndTime": row[4],
                                }
                                for row in output_prev_week
                            ]

                            # Creating Adaptive Card
                            adaptive_card = {
                                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                                "type": "AdaptiveCard",
                                "version": "1.0",
                                "body": [
                                    {
                                        "type": "TextBlock",
                                        "text": "Previous Week Actual Working Hours"+ f"\n\nEmployeeName : {username}",
                                        "weight": "bolder",
                                        "size": "medium"
                                    },
                                    {
                                        "type": "ColumnSet",
                                        "columns": [
                                            # {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "EmployeeName"}] + [{"type": "TextBlock", "text": data["EmployeeName"]} for data in data_for_adaptive_card]},
                                            {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "Date"}] + [{"type": "TextBlock", "text": data["Date"]} for data in data_for_adaptive_card]},
                                            {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "Day"}] + [{"type": "TextBlock", "text": data["Day"]} for data in data_for_adaptive_card]},
                                            {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "ActualStartTime"}] + [{"type": "TextBlock", "text": data["ActualStartTime"]} for data in data_for_adaptive_card]},
                                            {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "ActualEndTime"}] + [{"type": "TextBlock", "text": data["ActualEndTime"]} for data in data_for_adaptive_card]},
                                        ]
                                    }
                                ]
                            }

                            # Sending the Adaptive Card
                            response_activity = MessageFactory.attachment(CardFactory.adaptive_card(adaptive_card))
                            await turn_context.send_activity(response_activity)

                            # Suggested Actions
                            follow_up_actions = SuggestedActions(
                                actions=[
                                    CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                                    CardAction(title="No", type=ActionTypes.im_back, value="No"),
                                    # Add more follow-up actions as needed
                                ]
                            )

                            # Follow-up text with suggested actions
                            follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                            follow_up_response.suggested_actions = follow_up_actions

                            # Sending the follow-up message
                            await turn_context.send_activity(follow_up_response)

                        elif entity == 'UpcomingWeek':
                            next_week_query = "SELECT EmployeeName,Date, Day, ScheduledStartTime, ScheduledEndTime FROM EmployeeSchedule WHERE ActualStartTime IS NULL AND EmployeeName = ?;"
                            sql_cursor.execute(next_week_query, username)
                            next_week_data = sql_cursor.fetchall()
                            response_activity = MessageFactory.text(f'Your Next Week working Hours info:')
                            print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^', list(next_week_data))

                            output_next_week = convert_dates(next_week_data)
                            print(output_next_week)
                            data_for_adaptive_card = [
                                {
                                    # "EmployeeName": row[0],
                                    "Date": str(row[1]),
                                    "Day": row[2],
                                    "ScheduledStartTime": row[3],
                                    "ScheduledEndTime": row[4],
                                }
                                for row in output_next_week
                            ]

                            # Creating Adaptive Card
                            adaptive_card = {
                                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                                "type": "AdaptiveCard",
                                "version": "1.0",
                                "body": [
                                    {
                                        "type": "TextBlock",
                                        "text": "Next Week Scheduled Working Hours " + f"\n\nEmployeeName : {username}",
                                    
                                        "weight": "bolder",
                                        "size": "medium"
                                    },
                                    {
                                        "type": "ColumnSet",
                                        "columns": [
                                            # {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": data["EmployeeName"]} for data in data_for_adaptive_card]},
                                            {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "Date"}] +[{"type": "TextBlock", "text": data["Date"]} for data in data_for_adaptive_card]},
                                            {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "Day"}] + [{"type": "TextBlock", "text": data["Day"]} for data in data_for_adaptive_card]},
                                            {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "ScheduledStartTime"}] + [{"type": "TextBlock", "text": data["ScheduledStartTime"]} for data in data_for_adaptive_card]},
                                            {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": "ScheduledEndTime"}] + [{"type": "TextBlock", "text": data["ScheduledEndTime"]} for data in data_for_adaptive_card]},
                                        ]
                                    }
                                ]
                            }

                            # Sending the Adaptive Card
                            response_activity = MessageFactory.attachment(CardFactory.adaptive_card(adaptive_card))
                            await turn_context.send_activity(response_activity)

                            # Suggested Actions
                            follow_up_actions = SuggestedActions(
                                actions=[
                                    CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                                    CardAction(title="No", type=ActionTypes.im_back, value="No"),
                                    # Add more follow-up actions as needed
                                ]
                            )

                            # Follow-up text with suggested actions
                            follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                            follow_up_response.suggested_actions = follow_up_actions

                            # Sending the follow-up message
                            await turn_context.send_activity(follow_up_response)


                            # await turn_context.send_activity(response_activity)
                        # else: 
                        #     '''Give schedule for two weeks'''
                        #     all_week_query = "SELECT Date, Day, ScheduledStartTime, ScheduledEndTime,ActualStartTime,ActualStartTime FROM EmployeeSchedule WHERE EmployeeName = ?;"
                        #     sql_cursor.execute(all_week_query, username)
                        #     sql_cursor.execute(all_week_query, username)
                        #     all_week_data = sql_cursor.fetchall()
                        #     response_activity = MessageFactory.text(f'Your Last Week working Hours info:')

                            # await turn_context.send_activity(response_activity)

                        # LWH_query ='SELECT * FROM EmployeeSchedule WHERE EmployeeName = ? AND Date = ? ;'
                        # UWH_query ='SELECT * FROM EmployeeSchedule WHERE EmployeeName = ? AND Date = ?  ;'

                        # sql_cursor.execute(LWH_query, username, date)
                        # LWH_data = sql_cursor.fetchone()
                        # response_activity = MessageFactory.text(f'Your Last Week working Hours info:')
                        # # await turn_context.send_activity(response_activity)
                        # if LWH_data:
                        #     # Assuming the columns in payslips table are in the order of: EmployeeName, Salary, Deductions, NetPay
                        #     employeename,employeeid ,Date, Day, ScheduledStartTime,ScheduledEndTime, ActualStartTime, ActualEndTime, ScheduledWorkingHours,ActualWorkingHours = LWH_data
                        #     # card_color = "Red"
                        #     # Create a Hero Card to display payslip information
                        #     LWH_hero_card = HeroCard(
                        #                                 title="Last Week Working Hours Info",
                        #                                 text=(
                        #                                         f"**Employee:** {employeename}\n\n "
                        #                                         f"**EmployeeID:** {employeeid}\n\n "
                        #                                         f"| **Day** | **Date** | **Actual Start Time** | **Actual End Time** |\n"
                        #                                         f"| --- | --- | --- | --- |\n"  # Table header separator
                        #                                         f"| {Day} | {Date} | {ActualStartTime} to {ActualEndTime} |\n"
                        #                                     ),
                        #                                 )


                        #     # Send the Hero Card as an attachment
                        #     response_activity = MessageFactory.attachment(CardFactory.hero_card(LWH_hero_card))
                        #     await turn_context.send_activity(response_activity)
                        #     follow_up_actions = SuggestedActions(
                        #         actions=[
                        #             CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                        #             CardAction(title="No", type=ActionTypes.im_back, value="No"),
                        #             # Add more follow-up actions as needed
                        #         ]
                        #     )
                        #     follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                        #     follow_up_response.suggested_actions = follow_up_actions
                        #     await turn_context.send_activity(follow_up_response)
               
            else:
                print('Debug: Unkown Intent')
                file_path = r"Guardsman Group FAQ.docx"
                query_options = [file_path]
                human_query = question
                text_splitter=RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
                # llm = AzureChatOpenAI(deployment_name='gpt-0301', temperature = 0)
                llm = AzureOpenAI(deployment_name='gpt-0301', temperature = 0)
                memory = ConversationBufferMemory(memory_key="chat_history", input_key = 'human_input')
 
                response,_ = pdf_query_updated(query = human_query, text_splitter = text_splitter, llm = llm, query_options = ["Guardsman Group FAQ.docx"], memory = memory)
 
                response_activity = MessageFactory.text(response)
       
                await turn_context.send_activity(response_activity)   
                follow_up_actions = SuggestedActions(
                    actions=[
                        CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                        CardAction(title="No", type=ActionTypes.im_back, value="No"),
                        # Add more follow-up actions as needed
                    ]
                )
                follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                follow_up_response.suggested_actions = follow_up_actions
                await turn_context.send_activity(follow_up_response)
   
                
                

                

                # elif best_intent == "GetWorkingHours":

                #     # dialog = GetWorkingHoursDialog()
                #     # return await turn_context.begin_dialog(dialog.id, {"username": username})

                #     # # Call the get_working_hours_dialog function
                #     # working_hours_dialog = get_working_hours_dialog()
                #     # # Add the dialog to your DialogSet or wherever you manage your dialogs
                #     # dialog_set.add(working_hours_dialog)
                #     # # Start the dialog
                #     # await dialog_set.begin_dialog(working_hours_dialog.id)
                #     conn_string = get_connection_string()
                #     sql_connection = pyodbc.connect(conn_string)
                #     sql_cursor = sql_connection.cursor()

                #     WH_query = 'SELECT * FROM EmployeeSchedule WHERE EmployeeName = ? and date = ?;'
                #     sql_cursor.execute(WH_query, username, date)
                #     WH_data = sql_cursor.fetchone()
                #     response_activity = MessageFactory.text(f'Your working Hous info:')
                #     # await turn_context.send_activity(response_activity)
                #     if WH_data:
                #         # Assuming the columns in payslips table are in the order of: EmployeeName, Salary, Deductions, NetPay
                #         employeename,employeeid ,Date, Day, ScheduledStartTime,ScheduledEndTime, ActualStartTime, ActualEndTime, ScheduledWorkingHours,ActualWorkingHours = WH_data
                #         # card_color = "Red"
                #         # Create a Hero Card to display payslip information
                #         payslip_hero_card = HeroCard(
                #                                     title="WorkingHours Info",
                #                                     text=(
                #                                         f"**Employee:** {employeename}\n\n "
                #                                         f"**EmployeeID:** {employeeid}\n\n "
                #                                         f"**Date:** {Date}\n\n"
                #                                         f"**Day:** {Day}\n\n"
                #                                         f"**ScheduledStartTime:** {ScheduledStartTime}\n\n"
                #                                         f"**ScheduledEndTime:** {ScheduledEndTime}\n\n"
                #                                         f"**ActualStartTime:** {ActualStartTime}\n\n"
                #                                         f"**ActualEndTime:** {ActualEndTime}\n\n"
                #                                         f"**ScheduledWorkingHours:** {ScheduledWorkingHours}\n\n"
                #                                         f"**ActualWorkingHours:** {ActualWorkingHours}"

                #                                     ),
                #                                     #  background_image=f"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAWElEQVR42mP8/5+h/H8A53/A5j4zEG8rA6vDp/wMWCg4iXg9IbIBvE9L1CBUII6xEMw5WUiVIkgFA0eL8AxgCoL5AAAAAElFTkSuQmCC",
                #                                     # border_color=card_color
                #         )


                #         # Send the Hero Card as an attachment
                #         response_activity = MessageFactory.attachment(CardFactory.hero_card(payslip_hero_card))
                #         await turn_context.send_activity(response_activity)
                #         follow_up_actions = SuggestedActions(
                #             actions=[
                #                 CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
                #                 CardAction(title="No", type=ActionTypes.im_back, value="No"),
                #                 # Add more follow-up actions as needed
                #             ]
                #         )
                #         follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
                #         follow_up_response.suggested_actions = follow_up_actions
                #         await turn_context.send_activity(follow_up_response)
                            



    async def on_members_added_activity(
        self,
        members_added: ChannelAccount,
        turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                welcome_message = "Hi, Welcome to Guardsman!\n\nWith what can I help you with today?"

                suggested_actions = SuggestedActions(
                    actions=[
                        CardAction(title="Leave Management", type=ActionTypes.im_back, value="Leave Management"),
                        CardAction(title="Get Working Hours", type=ActionTypes.im_back, value="Get Working Hours"),
                        CardAction(title="Payroll Details", type=ActionTypes.im_back, value="Payroll Details"),
                        CardAction(title="About Organization", type=ActionTypes.im_back, value="About Organization")
                    ]
                )
                # Greet new members
                response_activity = MessageFactory.text(welcome_message)
                response_activity.suggested_actions = suggested_actions
                await turn_context.send_activity(response_activity)


#--------------------------------------------------------------------------------------




    # from botbuilder.dialogs import WaterfallDialog, WaterfallStepContext, DialogTurnResult
    # from botbuilder.dialogs.prompts import TextPrompt, PromptOptions
    # from botbuilder.core import MessageFactory, SuggestedActions, ActionTypes, CardAction
    # from botbuilder.schema import HeroCard
    # import pyodbc

    # def get_working_hours_dialog(dialog_id: str = None):
    #     dialog = WaterfallDialog(
    #         dialog_id or WaterfallDialog.__name__,
    #         [
    #             prompt_for_date,
    #             retrieve_working_hours,
    #             final_step,
    #         ],
    #     )

    #     dialog.add_dialog(TextPrompt(TextPrompt.__name__))

    #     return dialog

    # async def prompt_for_date(step_context: WaterfallStepContext) -> DialogTurnResult:
    #     # Ask the user for the date
    #     return await step_context.prompt(
    #         TextPrompt.__name__,
    #         PromptOptions(prompt=MessageFactory.text("Please provide the date for which you want to retrieve working hours.")),
    #     )

    # async def retrieve_working_hours(step_context: WaterfallStepContext) -> DialogTurnResult:
    #     # Retrieve the user's response and store it in the step context
    #     step_context.values["date"] = step_context.result

    #     # Assuming you have the employee name stored in the step context
    #     username = step_context.options["username"]

    #     # Execute the database query with both employee name and date
    #     conn_string = get_connection_string()
    #     sql_connection = pyodbc.connect(conn_string)
    #     sql_cursor = sql_connection.cursor()
    #     WH_query = 'SELECT * FROM EmployeeSchedule WHERE EmployeeName = ? and date = ?;'
    #     sql_cursor.execute(WH_query, username, step_context.result)
    #     WH_data = sql_cursor.fetchone()

    #     # Store the retrieved data in the step context
    #     if WH_data:
    #         step_context.values["WH_data"] = WH_data
    #     else:
    #         step_context.values["WH_data"] = None

    #     # Move to the next step
    #     return await step_context.next()

    # async def final_step(step_context: WaterfallStepContext) -> DialogTurnResult:
    #     # Display the working hours information or a message if no data was found
    #     WH_data = step_context.values["WH_data"]
    #     if WH_data:
    #         # Display the working hours information
    #         employeename, employeeid, Date, Day, ScheduledStartTime, ScheduledEndTime, ActualStartTime, ActualEndTime, ScheduledWorkingHours, ActualWorkingHours = WH_data
    #         card_color = "Red"
    #         payslip_hero_card = HeroCard(
    #             title="WorkingHours Info",
    #             text=(
    #                 f"**Employee:** {employeename}\n\n "
    #                 f"**EmployeeID:** {employeeid}\n\n "
    #                 f"**Date:** {Date}\n\n"
    #                 f"**Day:** {Day}\n\n"
    #                 f"**ScheduledStartTime:** {ScheduledStartTime}\n\n"
    #                 f"**ScheduledEndTime:** {ScheduledEndTime}\n\n"
    #                 f"**ActualStartTime:** {ActualStartTime}\n\n"
    #                 f"**ActualEndTime:** {ActualEndTime}\n\n"
    #                 f"**ScheduledWorkingHours:** {ScheduledWorkingHours}\n\n"
    #                 f"**ActualWorkingHours:** {ActualWorkingHours}"
    #             ),
    #             background_image=f"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAWElEQVR42mP8/5+h/H8A53/A5j4zEG8rA6vDp/wMWCg4iXg9IbIBvE9L1CBUII6xEMw5WUiVIkgFA0eL8AxgCoL5AAAAAElFTkSuQmCC",
    #             border_color=card_color
    #         )
    #         response_activity = MessageFactory.attachment(CardFactory.hero_card(payslip_hero_card))
    #         await step_context.context.send_activity(response_activity)
    #     else:
    #         # Display a message if no data was found
    #         await step_context.context.send_activity("No working hours data found for the given date.")

    #     # Ask if the user wants to know anything else
    #     follow_up_actions = SuggestedActions(
    #         actions=[
    #             CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
    #             CardAction(title="No", type=ActionTypes.im_back, value="No"),
    #         ]
    #     )
    #     follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
    #     follow_up_response.suggested_actions = follow_up_actions
    #     await step_context.context.send_activity(follow_up_response)

    #     # End the dialog
    #     return await step_context.end_dialog()

# Include the get_connection_string function here

#_____________________________________________________________________________________________________________________class
    # class GetWorkingHoursDialog(ComponentDialog):
    #     def __init__(self, dialog_id: str = None):
    #         super(GetWorkingHoursDialog, self).__init__(dialog_id or GetWorkingHoursDialog.__name__)

    #         self.add_dialog(
    #             WaterfallDialog(
    #                 WaterfallDialog.__name__,
    #                 [
    #                     self.prompt_for_date,
    #                     self.retrieve_working_hours,
    #                     self.final_step,
    #                 ],
    #             )
    #         )

    #         self.add_dialog(TextPrompt(TextPrompt.__name__))

    #         self.initial_dialog_id = WaterfallDialog.__name__

    #     async def prompt_for_date(self, step_context: WaterfallStepContext) -> DialogTurnResult:
    #         # Ask the user for the date
    #         return await step_context.prompt(
    #             TextPrompt.__name__,
    #             PromptOptions(prompt=MessageFactory.text("Please provide the date for which you want to retrieve working hours.")),
    #         )

    #     async def retrieve_working_hours(self, step_context: WaterfallStepContext) -> DialogTurnResult:
    #         # Retrieve the user's response and store it in the step context
    #         step_context.values["date"] = step_context.result

    #         # Assuming you have the employee name stored in the step context
    #         username = step_context.options["username"]

    #         # Execute the database query with both employee name and date
    #         conn_string = get_connection_string()
    #         sql_connection = pyodbc.connect(conn_string)
    #         sql_cursor = sql_connection.cursor()
    #         WH_query = 'SELECT * FROM EmployeeSchedule WHERE EmployeeName = ? and date = ?;'
    #         sql_cursor.execute(WH_query, username, step_context.result)
    #         WH_data = sql_cursor.fetchone()

    #         # Store the retrieved data in the step context
    #         if WH_data:
    #             step_context.values["WH_data"] = WH_data
    #         else:
    #             step_context.values["WH_data"] = None

    #         # Move to the next step
    #         return await step_context.next()

    #     async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
    #         # Display the working hours information or a message if no data was found
    #         WH_data = step_context.values["WH_data"]
    #         if WH_data:
    #             # Display the working hours information
    #             employeename, employeeid, Date, Day, ScheduledStartTime, ScheduledEndTime, ActualStartTime, ActualEndTime, ScheduledWorkingHours, ActualWorkingHours = WH_data
    #             card_color = "Red"
    #             payslip_hero_card = HeroCard(
    #                 title="WorkingHours Info",
    #                 text=(
    #                     f"**Employee:** {employeename}\n\n "
    #                     f"**EmployeeID:** {employeeid}\n\n "
    #                     f"**Date:** {Date}\n\n"
    #                     f"**Day:** {Day}\n\n"
    #                     f"**ScheduledStartTime:** {ScheduledStartTime}\n\n"
    #                     f"**ScheduledEndTime:** {ScheduledEndTime}\n\n"
    #                     f"**ActualStartTime:** {ActualStartTime}\n\n"
    #                     f"**ActualEndTime:** {ActualEndTime}\n\n"
    #                     f"**ScheduledWorkingHours:** {ScheduledWorkingHours}\n\n"
    #                     f"**ActualWorkingHours:** {ActualWorkingHours}"
    #                 ),
    #                 background_image=f"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAWElEQVR42mP8/5+h/H8A53/A5j4zEG8rA6vDp/wMWCg4iXg9IbIBvE9L1CBUII6xEMw5WUiVIkgFA0eL8AxgCoL5AAAAAElFTkSuQmCC",
    #                 border_color=card_color
    #             )
    #             response_activity = MessageFactory.attachment(CardFactory.hero_card(payslip_hero_card))
    #             await step_context.context.send_activity(response_activity)
    #         else:
    #             # Display a message if no data was found
    #             await step_context.context.send_activity("No working hours data found for the given date.")

    #         # Ask if the user wants to know anything else
    #         follow_up_actions = SuggestedActions(
    #             actions=[
    #                 CardAction(title="Yes", type=ActionTypes.im_back, value="Yes"),
    #                 CardAction(title="No", type=ActionTypes.im_back, value="No"),
    #             ]
    #         )
    #         follow_up_response = MessageFactory.text("Is there anything else you would like to know?")
    #         follow_up_response.suggested_actions = follow_up_actions
    #         await step_context.context.send_activity(follow_up_response)

    #         # End the dialog
    #         return await step_context.end_dialog()
        #_________________________________________________________________________end(class)
        
        #-------------------------------------------------------------------------------------------------------
