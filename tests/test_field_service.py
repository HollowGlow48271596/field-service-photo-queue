from field_service import FollowUp, WorkOrderPhoto


def test_follow_up_records_ready_dispatch_state():
    photo = WorkOrderPhoto("WO-1042", "tech-17", "meter.jpg", "image-data")

    result = FollowUp(photo.work_order_id, photo.technician_id, "img-77", "ready_for_dispatch")

    assert result == FollowUp("WO-1042", "tech-17", "img-77", "ready_for_dispatch")
