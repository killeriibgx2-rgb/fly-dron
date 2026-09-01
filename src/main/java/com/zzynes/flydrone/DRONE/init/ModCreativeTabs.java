package com.zzynes.flydrone.DRONE.init;

import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.RegistryObject;

public class ModCreativeTabs {
    public static final DeferredRegister<CreativeModeTab> CREATIVE_TABS =
            DeferredRegister.create(Registries.CREATIVE_MODE_TAB, "fly_drone");

    public static final RegistryObject<CreativeModeTab> FLY_DRONE_TAB = CREATIVE_TABS.register("fly_drone_tab",
            () -> CreativeModeTab.builder()
                    .title(Component.translatable("itemGroup.fly_drone"))
                    .icon(() -> new ItemStack(ModItems.BATTERY.get()))
                    .displayItems((parameters, output) -> {
                        output.accept(ModItems.ALUMINUM_INGOT.get());
                        output.accept(ModItems.LITHIUM_INGOT.get());
                        output.accept(ModItems.COPPER_WIRE.get());
                        output.accept(ModItems.BATTERY.get());
                        output.accept(ModItems.REMOTE_CONNECTED.get());
                        output.accept(ModItems.REMOTE_DISCONNECTED.get());
                        output.accept(ModItems.ALUMINUM_ORE.get());
                        output.accept(ModItems.LITHIUM_ORE.get());
                        output.accept(ModItems.BATTERY_CELL.get());
                        output.accept(ModItems.CAMERA_FPV.get());
                        output.accept(ModItems.COPPER_PLATE.get());
                        output.accept(ModItems.IRON_PLATE.get());
                        output.accept(ModItems.LITHIUM_PLATE.get());
                        output.accept(ModItems.MICROCONTROLLER.get());
                        output.accept(ModItems.MOTOR_CASING.get());
                        output.accept(ModItems.MOTOR_FPV.get());
                        output.accept(ModItems.MOTOR_SHAFT.get());
                        output.accept(ModItems.MOTOR_WINDING.get());
                        output.accept(ModItems.PROPELLER_FPV.get());
                        output.accept(ModItems.SANDWICH_PANEL.get());
                        output.accept(ModItems.FPV_DRONE_ITEM.get());
                        output.accept(ModItems.STAL_MOLOT.get());
                    })
                    .build());

    public static void register(IEventBus eventBus) {
        CREATIVE_TABS.register(eventBus);
    }
}