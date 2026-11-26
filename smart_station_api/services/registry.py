from . import hr_features, school_features

FEATURE_LIST = [
    hr_features.AttendanceFeature(),
    hr_features.TimeOffFeature(),
    hr_features.AllocationFeature(),
    hr_features.GeneralRequestFeature(),
    hr_features.AdjustmentFeature(),
    hr_features.PayslipFeature(),
    hr_features.AppraisalFeature(),
    hr_features.AbsentEmployeesFeature(),
    hr_features.JobDescriptionFeature(),
    school_features.StudentAttendanceFeature(),
    school_features.StudentExamFeature(),
    school_features.SchoolMoldFeature(),
    school_features.ViolationFeature(),
    school_features.CaseStudyFeature(),
]
FEATURES = {feature.key: feature for feature in FEATURE_LIST}
TILES = sorted(
    [hr_features.ProfileTile(), hr_features.TakeAttendanceTile()] + FEATURE_LIST,
    key=lambda item: item.sequence,
)
