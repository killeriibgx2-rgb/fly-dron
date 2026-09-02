package com.zzynes.flydrone.DRONE.init;

import com.zzynes.flydrone.DRONE.FlyDroneMod;
import com.zzynes.flydrone.DRONE.entity.FpvDroneEntity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

public class ModEntityTypes {
    public static final DeferredRegister<EntityType<?>> ENTITY_TYPES =
            DeferredRegister.create(ForgeRegistries.ENTITY_TYPES, FlyDroneMod.MOD_ID);

    public static final RegistryObject<EntityType<FpvDroneEntity>> FPV_DRONE = ENTITY_TYPES.register("fpv_drone",
            () -> EntityType.Builder.of(FpvDroneEntity::new, MobCategory.MISC)
                    .sized(0.8f, 0.4f)
                    .clientTrackingRange(256)
                    .updateInterval(3)
                    .build("fpv_drone"));

    public static void register(IEventBus eventBus) {
        ENTITY_TYPES.register(eventBus);
    }

    public static AttributeSupplier createDroneAttributes() {
        return AttributeSupplier.builder()
                .add(Attributes.MAX_HEALTH, 5.0)
                .add(Attributes.MOVEMENT_SPEED, 0.0)
                .add(Attributes.FLYING_SPEED, 0.0)
                .add(Attributes.FOLLOW_RANGE, 16.0)
                .build();
    }
}