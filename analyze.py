import findstays, calculatepar, calculatescore, sqlalchemy, sqlalchemy.orm
from sqlalchemy.orm import sessionmaker 
import time

def main():
    t = time.time()
    password = ""
    for line in open("password.txt"):
        password += line
    engine = sqlalchemy.create_engine(f"mysql://root:{password}@localhost:3306/CovidAlerter")
    Session = sessionmaker(bind=engine)
    session = Session()
    calculatepar.calculate(session)
    print("Time (ms): " + str((time.time() - t) * 1000))
    input("Press any key to exit...")

if __name__ == "__main__":
    main()
