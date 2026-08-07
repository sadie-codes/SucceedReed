from typing import List
from sqlalchemy import create_engine, ForeignKey, select, String, Integer, Float, DateTime, inspect
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase, Session
from datetime import date, datetime
import math
from sqlalchemy import inspect

#represents the optimal playing time for each day that the reed is broken in
BREAK_IN_SCHEDULE = [5, 5, 10, 15, 20]

#custom declarative base class, to transform Python classes into ORM SQLAlchemy models
class Base(DeclarativeBase):
    pass


class ReedSession(Base):
    """Represents a practice session using a specific reed from the database

    Practice Sessions are stored in a list in the Reed class and are always associated with a reed
    Inherits from base to be tied to the SQLAlchemy database.

    Attributes:
        date: A datetime type that represents the date the session was added. This is the primary key.
        rating: A string that represents how good the session was. Can be "good", "ok", or "bad".
        minutes: An integer indicating how long a practice session lasted.
        parent_id: A string representing the id of which reed was used. ForeignKey associated with parent table.
    """

    __tablename__ = "sessions"
    date: Mapped[datetime] = mapped_column(DateTime(), primary_key=True)
    rating: Mapped[str] = mapped_column(String())
    minutes: Mapped[int] = mapped_column(Integer())
    parent_id: Mapped[str] = mapped_column(ForeignKey("reeds.db_id"))

    #back populates with the reed class to syncronize changes across the two classes.
    #each session is put in a list as an attribute of a Reed object, so back_populates is used to sync changes.
    reed: Mapped["Reed"] = relationship(back_populates="sessions")

    #used to turn a rating into a number so a health score can be calculated
    RATING_CONVERT = {
                      "good":2,
                      "ok":0,
                      "bad" :-2
                    }
    #represents the decreasing factor that is applied to health score when a reed is overplayed.
    #Ex. If a reed is very overplayed, the health score is reduced to 80% of the original health.
    VERY_OVERPLAYED = .8
    SLIGHTLY_OVERPLAYED = .9

    #Used in the calculation of the healthscore, to determine how old sessions can be to still have an impact on the score
    #in this case, sessions from the past 2 weeks or 14 days have the most weight in the health score since they were the most recent
    WEIGHT_DECAY_DAYS = 14
        
    @property
    def days_ago(self):
        """The number of days old the session is."""
        days_ago = (datetime.now() - self.date).days
        return days_ago

    def convert_rating(self, word_rating):
        return ReedSession.RATING_CONVERT.get(word_rating.lower(), 0)
    
    def get_weight(self):
        """Returns the weight of a session based on how many days ago it was

        Args:
            self: an object of the ReedSession type.
        Returns:
            A float representing the weight of the function.
            The weight is determined using the exponential decay function: y=e^(-x/w)
            Where y represents the weight returned, x represents how long ago the session was, and w is the weight each day ago has
        """
        weight = math.exp(-self.days_ago / ReedSession.WEIGHT_DECAY_DAYS) #sessions from the last 2 weeks have major impact
        return weight

    def get_weighted_rating(self):
        """Returns the weighted rating based on the weight of the function.

        Args:
            self: an object of the ReedSession type.
        
        Returns:
            A float representing the weighted rating.
            The rating is determined using this formula: numeric rating * session weight * overplayed factor.
            Ratings that are worse and overplayed have a lower rating and vice versa.
            The session weight increases the factor by which the rating is increased or decreased, depending on how long ago the session was.
        """
        rating_numeric = self.convert_rating(self.rating)
        weighted_value = rating_numeric *(self.get_weight())
        if self.reed.determine_if_overplayed(self) == "Very Overplayed":
            weighted_value *= ReedSession.VERY_OVERPLAYED
        elif self.reed.determine_if_overplayed(self) == "Slightly Overplayed":
            weighted_value *= ReedSession.SLIGHTLY_OVERPLAYED
        return weighted_value
    
    def to_dict(self):
        #turns the date into a string to be json serializable
        return {
            "date": self.date.isoformat(),
            "rating": self.rating,
            "minutes": self.minutes,
            "parent_id": self.parent_id
        }

    def __repr__(self):
        return f"ReedSession(date={self.date!r}, rating={self.rating!r}, minutes={self.minutes!r}, parent_id={self.parent_id!r}), reed={self.reed!r}"

def start_engine():
    """Starts the database to enable changes and returns the engine for use.

    Return:
        An Engine object representing the data base engine from SQLAlchemy.
        This is used to create database Sessions for changing and obtaining data.
    """
    engine = create_engine("sqlite:///reeddb.db", echo=True)
    Base.metadata.create_all(engine)
    return engine

def sortby(attribute, reed_list):
        """Returns a sorted list from greatest to least based on the attribute given.

        Args:
            attribute: an attribute of a class of any data type that can be compared using < and > (typically a number)
            reed_list: a list of objects that contains the attribute given.
        
        Returns:
            A list containing the reed_list given in a sorted order from greatest to least.
        """
        sorted_list = []
        for item in reed_list:
            inserted = False
            #since the attribute is unknown, the original obj.attribute accessing won't work, so the dunder method is used
            reed_rec = item.__getattribute__(attribute)
            if sorted_list:
                for r in range(len(sorted_list)):
                    other_item = sorted_list[r]
                    other_rec = other_item.__getattribute__(attribute)
                    #as items are added to the sorted list, they are compared with the current list to determine its place
                    if reed_rec > other_rec:
                        sorted_list.insert(r, item)
                        #inserted is used to determine whether the item needs to go at the end of the list
                        inserted = True
                        break
                if not(inserted):
                    #inserted is false if the item is the least among the list, therefore being at the end
                    sorted_list.append(item)
            else:
                sorted_list.append(item)
        return sorted_list



class Reed(Base):
    """Represents a reed that the user is playing on or has added
    
        Reeds are stored in a SQLAlchemy database and are associated with ReedSessions.
        Each reed needs to go through the break-in process before being regularly played, so the step is 1 by default.
        Each session increases the step by 1 until it is over 5. Then, it is changed to None indicating the reed is fully broken in.
        Each step is associated with an optimal amount of playing time according to the BREAK_IN_SCHEDULE list.
    
        Attributes:
            db_id: An integer that auto increments to uniquely identify each reed, since users could have a reed with the same name.
            id: A string that represents the user-chosen key to identify the reed. The primary key.
            reed_type: A string that represents the type of the reed.
            user_id: A string that represents the id of the user who added it.
            strength: A float that represents the strength of the reed (also known as the thickness).
            break_in_date: A datetime type that represents when the reed was first added.
            step: An integer 1-5 or None that represents how far along the user is to breaking in the reed (1 by default).
            minutes_played: An integer that represents the total time the user has played the reed.
            sessions: A list of ReedSession objects that holds all of the practice sessions the user has logged.
        """
    __tablename__ = "reeds"
    db_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String())
    user_id: Mapped[str] = mapped_column(String())
    reed_type: Mapped[str] = mapped_column(String())
    strength: Mapped[float] = mapped_column(Float())

    break_in_date: Mapped[datetime] = mapped_column(DateTime(), default=datetime.now())
    step: Mapped[int] = mapped_column(Integer(), default=1, nullable=True)
    minutes_played: Mapped[int] = mapped_column(Integer(), default=0)
    sessions: Mapped[List["ReedSession"]] = relationship(back_populates="reed", cascade="all, delete")

    #recommended playing time of a reed that is broken in or has step = "None"
    #if the length of a session exceeds this, the overplayed factor is applied to the rating
    NORMAL_TIME = 40

    #reeds have to rest at least 1 day to be considered "rested"
    DAYS_TO_REST = 1

    def __repr__(self):
        return f"Reed(db_id={self.db_id!r}, id={self.id!r}, user_id={self.user_id!r}, reed_type={self.reed_type!r}, strength={self.strength!r}, break_in_date={self.break_in_date!r}, step={self.step!r}, minutes_played={self.minutes_played!r}, sessions={self.sessions!r}"
    
    @property
    def recommended_time(self):
        """An integer that represents the recommended length of a session in minutes"""
        if self.step != None:
            rec_time = BREAK_IN_SCHEDULE[self.step-1]
            return rec_time
        return Reed.NORMAL_TIME
    
    @property
    def latest_session(self):
        """A ReedSession object that represents the latest practice session. None if no sessions."""
        if len(self.sessions) > 0:
            return self.sessions[-1]
        return None
    
    @property
    def health_score(self):
        """A float that represents the reed's health score."""
        new_health = 100
        total_ratings = 0
        total_weights = 0
        if len(self.sessions) > 0:
            for session in self.sessions:
                #adds up the totals for each session's weight and weighted rating to get an average number
                total_ratings += session.get_weighted_rating()
                total_weights += session.get_weight()
            #the unnormalized number gets the average rating depending on the weights
            #Sessions that were more recent have a greater say in the overall health of the reed
            un_normalized = total_ratings/total_weights
            #health is normalized to get a health number out of 100
            new_health = (un_normalized + 2)/4 * 100
        
        return round(new_health, 2)
    @property
    def is_rested(self):
        """A boolean that represents if a reed is 'rested' based on how long it hasn't been played"""
        if self.days_last_played < Reed.DAYS_TO_REST:
            return False
        return True
    @property
    def days_last_played(self):
        """An integer representing how many days a reed hasn't been played"""
        if len(self.sessions) > 0:
            days_ago = self.latest_session.days_ago
            return days_ago
        return (datetime.now() - self.break_in_date).days
    
    def delete_reed(self, db_session: Session):
        db_session.delete(self)
        db_session.commit()

    def determine_if_overplayed(self, session: ReedSession):
        """Determines if a reed has exceeded the recommeneded playing time in a session.

        Args:
            session: A ReedSession object that represents the practice session in question.
        
        Returns:
            A string that indicates how overplayed a reed is.
            "Very Overplayed" if the length of the session is over 1.75x the recommended time.
            "Slightly Overplayed" if the length of the session is over the recommended time or up to 1.75x the recommended time.
            "Not Overplayed" if the length of the session is under or exactly the recommended time.
        """
        if session.minutes > self.recommended_time:
            if session.minutes > (self.recommended_time * .75) + self.recommended_time:
                return "Very Overplayed"
            else:
                return "Slightly Overplayed"
        else:
            return "Not Overplayed"
    
    def update_daily_info(self):
        """Updates the reed info to match recent sessions logged

        Updates attributes, like step and minutes_played, that aren't properties.
        Properties are automatically updated when they are called, but the attributes aren't.
        The values are updated to represent the information from the current sessions logged.

        Args:
            self: A Reed object that the function is called on.

        Returns:
            None
        """
        self.step = len(self.sessions) + 1
        if self.step  > len(BREAK_IN_SCHEDULE):
            #if the step is above 5, the reed is fully broken in
            self.step = None
        self.minutes_played = 0
        for session in self.sessions:
            self.minutes_played += session.minutes

    @classmethod
    def recommended_reeds(cls, cur_id, db_session: Session):
        """Obtains a list of the recommended reeds in order of health score and most rested

        Args:
            cls: Reed class to call the method, since it is a class method.
            cur_id: This is the current id of the user using the application.
            db_session: An active SQLAlchemy Session object.

        Returns:
            A list containing Self@Reed objects.
            It is sorted by health score, with the reeds that are rested first.
        """

        #selects the Reed class from the table and returns the reeds in a Sequence to sort
        all_reeds = db_session.scalars(select(cls).where(cls.user_id == cur_id)).all()
        #the reeds are put in a python list, instead of a Sequence
        #while the list contains Self@Reed (ORM objects), this gets transformed into a dictionary to send to JS
        rec_reeds = []
        #ensures that the recommended reeds are playing reeds, not break in reeds
        for reed in all_reeds:
            if reed.step == None:
                rec_reeds.append(reed)
        health_score_sorted =  sortby("health_score", rec_reeds)
        #creates a copy of the list to not change the original
        with_rested_first = health_score_sorted[:]
        for reed in health_score_sorted:
            #rested reeds (have not been played at least one day) have priority over non-rested reeds
            if not reed.is_rested:
                with_rested_first.remove(reed)
                with_rested_first.append(reed)
        return with_rested_first

    @classmethod
    def rec_breakin_reeds(cls, cur_id, db_session: Session):
        """Obtains a list of the break-in reeds in order of health score and most rested
        
                Args:
                    cls: Reed class to call the method, since it is a class method.
                    cur_id: This is the current id of the user using the application.
                    db_session: An active SQLAlchemy Session object.
        
                Returns:
                    A list containing Self@Reed objects.
                    It is sorted by health score, with the reeds that are rested first.
                """
        session_exists = False
        #selects the Reed class from the table and returns the reeds in a Sequence to sort
        all_reeds = db_session.scalars(select(cls).where(cls.user_id == cur_id)).all()
        breakin_reeds = [r for r in all_reeds if r.step != None]
        
        for breakin_reed in breakin_reeds:
            if breakin_reed.sessions:
                session_exists = True
        #a session has to exist in order for the reeds to be sorted by days last played
        if session_exists:
            rec_breakin = sortby("days_last_played", breakin_reeds)
        else:
            rec_breakin = sortby("health_score", breakin_reeds)

        return rec_breakin
        
    @classmethod
    def get_all_info(cls, cur_id, db_session: Session):
        info = {}
        all_reeds = db_session.scalars(select(cls).where(cls.user_id == cur_id)).all()
        all_reeds = Reed.to_json_serializable(all_reeds)
        for reed in all_reeds:
            for attribute, value in reed.items():
                
                if str(attribute) in info:
                    info[str(attribute)].append(str(value))
                else:
                    info[str(attribute)] = [str(value)]
        return info

    @classmethod
    def to_json_serializable(cls, reed_list):
        """Returns a json_serializable dictionary of reed_objects to send to JS.

        JSON cannot read python objects, so it needs to be in a format of dictionaries and lists.

        Args:
            cls: Reed class for the method to be called on.
            reed_list: A list of Reed objects. 

        Returns:
            List of dictionaries representing each Reed object and its corresponding ReedSessions.
        """
       
        serialized = []
        for reed in reed_list:
            item_dict = {}
            #class attributes are mapped to columns and the keys of the database are retrieved
            #this is so we can access the attributes and values one by one for each reed
            for c in inspect(reed).mapper.column_attrs:
                #attains the attribute from the object and the string format of the attribute
                val = getattr(reed, c.key)
                #check if the attribute is datetime, to transform it into a string for json to read
                if isinstance(val, (datetime, date)):
                    val = val.isoformat()
                item_dict[c.key] = val

            #class properties are not present in the column_attrs call, so they need to be added indivually
            item_dict['sessions'] = []
            #transforms the sessions into a list of dictionaries, so json can read it
            for session in reed.sessions:
                item_dict['sessions'].append(session.to_dict())
            item_dict['recommended_time'] = reed.recommended_time
            item_dict['latest_session'] = reed.latest_session.to_dict() if reed.latest_session else {}
            item_dict['health_score'] = reed.health_score
            item_dict['days_last_played'] = reed.days_last_played
            item_dict['is_rested'] = reed.is_rested

            serialized.append(item_dict)
        return serialized
    



