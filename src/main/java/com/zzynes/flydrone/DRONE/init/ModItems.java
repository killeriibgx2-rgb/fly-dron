package com.zzynes.flydrone.DRONE.init;

import com.zzynes.flydrone.DRONE.item.DroneRemoteItem;
import com.zzynes.flydrone.DRONE.item.DroneSpawnItem;
import net.minecraft.world.item.Item;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

public class ModItems {
    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, "fly_drone");

    public static final RegistryObject<Item> ALUMINUM_INGOT = ITEMS.register("aluminum_ingot",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> LITHIUM_INGOT = ITEMS.register("lithium_ingot",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> COPPER_WIRE = ITEMS.register("copper_wire",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> BATTERY = ITEMS.register("battery",
            () -> new Item(new Item.Properties().stacksTo(1)));
    public static final RegistryObject<Item> REMOTE_CONNECTED = ITEMS.register("remote_connected",
            () -> new DroneRemoteItem(new Item.Properties().stacksTo(1), true));
    public static final RegistryObject<Item> REMOTE_DISCONNECTED = ITEMS.register("remote_disconnected",
            () -> new DroneRemoteItem(new Item.Properties().stacksTo(1), false));
    public static final RegistryObject<Item> ALUMINUM_ORE = ITEMS.register("aluminum_ore",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> LITHIUM_ORE = ITEMS.register("lithium_ore",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> BATTERY_CELL = ITEMS.register("battery_cell",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> CAMERA_FPV = ITEMS.register("camera_fpv",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> COPPER_PLATE = ITEMS.register("copper_plate",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> IRON_PLATE = ITEMS.register("iron_plate",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> LITHIUM_PLATE = ITEMS.register("lithium_plate",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> MICROCONTROLLER = ITEMS.register("microcontroller",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> MOTOR_CASING = ITEMS.register("motor_casing",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> MOTOR_FPV = ITEMS.register("motor_fpv",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> MOTOR_SHAFT = ITEMS.register("motor_shaft",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> MOTOR_WINDING = ITEMS.register("motor_winding",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> PROPELLER_FPV = ITEMS.register("propeller_fpv",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> SANDWICH_PANEL = ITEMS.register("sandwich_panel",
            () -> new Item(new Item.Properties()));
    public static final RegistryObject<Item> FPV_DRONE_ITEM = ITEMS.register("fpv_drone",
            () -> new DroneSpawnItem(new Item.Properties().stacksTo(1)));
    public static final RegistryObject<Item> STAL_MOLOT = ITEMS.register("stal_molot",
            () -> new Item(new Item.Properties().durability(250)));

    public static void register(IEventBus eventBus) {
        ITEMS.register(eventBus);
    }
}