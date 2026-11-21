import inspect, sys
sys.path.insert(0, ".")
import calling.army_subjects as a

names = [
    "order_execute_recipe",
    "new_front_recipe",
    "set_path_recipe",
    "order_assign_recipe",
    "set_order_group_execution_type_recipe",
    "order_edit_root_recipe",
    "set_army_leader_recipe",
    "order_set_invasion_source_recipe",
]
for n in names:
    fn = getattr(a, n)
    print("=" * 80)
    print(n)
    print(inspect.getsource(fn))
