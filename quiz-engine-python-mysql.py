import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Your_MySql_Password",
        database="quizengine"
    )

def register():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        name = input("enter your name: ").strip()
        email = input("enter your email: ").strip()
        password = input("enter your password: ")

        if not name or not email or not password:
            print("name, email and password cannot be empty.")
            return

        cursor.execute(
            "insert into users (name, email, password) values (%s, %s, %s)",
            (name, email, password)
        )
        conn.commit()
        print(f"Registered successfully! User ID: {cursor.lastrowid}")

    except mysql.connector.Error as e:
        if e.errno == 1062:
            print("this email is already registered.")
        else:
            print("Registration failed:", e)

    finally:
        cursor.close()
        conn.close()

def list_quizes():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "select quiz_id, title, total_time_min from quizes"
        )
        rows = cursor.fetchall()

        if not rows:
            print("no quizzes are available.")
            return

        print("\nAvailable quizes:")

        for row in rows:
            print(f"{row[0]}. {row[1]} ({row[2]} min)")

    except mysql.connector.Error as e:
        print("unable to load quizzes.")
        print("Database error:", e)

    finally:
        cursor.close()
        conn.close()

def login():
    conn = get_connection()
    cursor = conn.cursor(buffered=True)
    try:
        email = input("enter your email: ").strip()
        password = input("enter your password: ")

        if not email or not password:
            print("email and password cannot be empty.")
            return None

        cursor.execute(
            "select user_id, name from users where email=%s and password=%s",
            (email, password)
        )
        row = cursor.fetchone()

        if row:
            print(f"Welcome {row[1]}! (User ID: {row[0]})")
            return row[0]

        print("invalid email or password.")
        return None

    except mysql.connector.Error as e:
        print("login failed.")
        print("Database error:", e)
        return None

    finally:
        cursor.close()
        conn.close()

def take_quiz(current_user):
    conn = get_connection()
    cursor = conn.cursor()
    attempt_id = None

    try:
        cursor.execute(
            "select quiz_id, title from quizes"
        )
        rows = cursor.fetchall()

        if not rows:
            print("no quizzes are available.")
            return

        print("\nAvailable quizes are:")

        for row in rows:
            print(f"{row[0]}. {row[1]}")

        try:
            quiz_id = int(input("enter your quiz_id: "))
        except ValueError:
            print("please enter a valid numeric quiz ID.")
            return

        valid_quiz_ids = [row[0] for row in rows]

        if quiz_id not in valid_quiz_ids:
            print("invalid quiz ID.")
            return

        cursor.execute(
            "select ques_id, ques_text, marks from questions where quiz_id=%s",
            (quiz_id,)
        )
        questions = cursor.fetchall()

        if not questions:
            print("this quiz does not contain any questions.")
            return

        cursor.execute(
            "insert into attempts (user_id, quiz_id) values (%s, %s)",
            (current_user, quiz_id)
        )
        conn.commit()

        attempt_id = cursor.lastrowid
        total_marks = 0
        earned_marks = 0

        for i, q in enumerate(questions, 1):
            ques_id = q[0]
            ques_text = q[1]
            marks = q[2]

            print(f"\nQ{i}. {ques_text} ({marks} mark)")

            cursor.execute(
                "select op_id, op_text, is_correct from select_options where ques_id=%s",
                (ques_id,)
            )
            options = cursor.fetchall()

            if not options:
                print("no options available for this question.")
                continue

            total_marks += marks

            for idx, opt in enumerate(options):
                print(f"{chr(65 + idx)}) {opt[1]}")

            answer = input("your answer: ").strip().upper()

            if len(answer) != 1:
                print("invalid answer. Please enter a valid option.")

                cursor.execute(
                    "insert into user_answers "
                    "(ques_id, op_id, attempt_id, is_correct) "
                    "values (%s, %s, %s, %s)",
                    (ques_id, None, attempt_id, 0)
                )
                conn.commit()
                continue

            opt_index = ord(answer) - 65

            if 0 <= opt_index < len(options):
                op_id = options[opt_index][0]
                is_correct = 1 if options[opt_index][2] == 1 else 0

                if is_correct:
                    earned_marks += marks
                    print("Correct answer! ✓")
                else:
                    print("Wrong answer! ✗")

                cursor.execute(
                    "insert into user_answers "
                    "(ques_id, op_id, attempt_id, is_correct) "
                    "values (%s, %s, %s, %s)",
                    (ques_id, op_id, attempt_id, is_correct)
                )
                conn.commit()

            else:
                print("invalid option for this question.")

                cursor.execute(
                    "insert into user_answers "
                    "(ques_id, op_id, attempt_id, is_correct) "
                    "values (%s, %s, %s, %s)",
                    (ques_id, None, attempt_id, 0)
                )
                conn.commit()

        print(f"\nYour Score: {earned_marks}/{total_marks}")

        cursor.execute(
            "update attempts "
            "set total_marks=%s, earned_marks=%s, status='completed', finished_at=now() "
            "where attempt_id=%s",
            (total_marks, earned_marks, attempt_id)
        )
        conn.commit()

        print("Quiz completed successfully!")

    except mysql.connector.Error as e:
        conn.rollback()
        print("an error occurred while taking the quiz.")
        print("Database error:", e)

    finally:
        cursor.close()
        conn.close()

def result(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "select a.attempt_id, a.quiz_id, q.title, "
            "a.total_marks, a.earned_marks, a.status "
            "from attempts a "
            "join quizes q on a.quiz_id = q.quiz_id "
            "where a.user_id=%s and a.status='completed' "
            "order by a.attempt_id desc",
            (user_id,)
        )
        rows = cursor.fetchall()

        if not rows:
            print("you have not completed any quizzes yet.")
            return

        print("\nYour results:")

        for r in rows:
            print(
                f"Attempt ID: {r[0]} | "
                f"Quiz: {r[2]} | "
                f"Score: {r[4]}/{r[3]} | "
                f"Status: {r[5]}"
            )

    except mysql.connector.Error as e:
        print("unable to load your results.")
        print("Database error:", e)

    finally:
        cursor.close()
        conn.close()

def main():
    print("=== QUIZ ENGINE ===")
    current_user = None

    while True:
        print("\n1. Register")
        print("2. Login")
        print("3. List Quizes")
        print("4. Take Quiz")
        print("5. Result")
        print("6. Exit")

        try:
            choice = int(input("enter your choice: "))
        except ValueError:
            print("please enter a number from 1 to 6.")
            continue

        if choice == 1:
            register()
        elif choice == 2:
            current_user = login()
        elif choice == 3:
            list_quizes()
        elif choice == 4:
            if current_user is None:
                print("please login first bro.")
            else:
                take_quiz(current_user)
        elif choice == 5:
            if current_user is None:
                print("please login first bro.")
            else:
                result(current_user)
        elif choice == 6:
            print("Thank you for using Quiz Engine!")
            print("Bye Bye bro!")
            break
        else:
            print("invalid choice. Please select 1 to 6.")

main()
