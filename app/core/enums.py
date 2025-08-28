import enum

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    USER = "USER"

class UserPart(str, enum.Enum):
    HR = "HR"
    IOS = "IOS"
    Android = "Android"
    Frontend = "Frontend"
    Backend = "Backend"
    PM = "PM"
    Designer = "Designer"
    Marketer = "Marketer"
    Legal = "Legal"

class DeploymentState(str, enum.Enum):
    REQUEST = "REQUEST"
    RETURN = "RETURN"
    APPROVAL = "APPROVAL"

class OrderBy(str, enum.Enum):
    CREATED_AT_DESC = "CREATED_AT_DESC"
    CREATED_AT_ASC = "CREATED_AT_ASC"
    UPDATED_AT_DESC = "UPDATED_AT_DESC"
    UPDATED_AT_ASC = "UPDATED_AT_ASC"