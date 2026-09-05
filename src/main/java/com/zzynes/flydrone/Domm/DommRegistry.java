package com.zzynes.flydrone.Domm;

import com.zzynes.flydrone.DRONE.FlyDroneMod;
import net.minecraft.world.flag.FeatureFlags;
import net.minecraft.world.inventory.MenuType;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.network.IContainerFactory;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

public class DommRegistry {
    public static final DeferredRegister<Block> BLOCKS = DeferredRegister.create(ForgeRegistries.BLOCKS, FlyDroneMod.MOD_ID);
    public static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, FlyDroneMod.MOD_ID);
    public static final DeferredRegister<BlockEntityType<?>> BLOCK_ENTITIES = DeferredRegister.create(ForgeRegistries.BLOCK_ENTITY_TYPES, FlyDroneMod.MOD_ID);
    public static final DeferredRegister<MenuType<?>> MENUS = DeferredRegister.create(ForgeRegistries.MENU_TYPES, FlyDroneMod.MOD_ID);

    public static final RegistryObject<Block> DOMM_BODY = BLOCKS.register("domm_kip", DommBodyBlock::new);
    public static final RegistryObject<Block> DOMM_INTERFACE = BLOCKS.register("domm_pan", DommInterfaceBlock::new);

    public static final RegistryObject<Item> DOMM_BODY_ITEM = ITEMS.register("domm_kip", () -> new BlockItem(DOMM_BODY.get(), new Item.Properties()));
    public static final RegistryObject<Item> DOMM_INTERFACE_ITEM = ITEMS.register("domm_pan", () -> new BlockItem(DOMM_INTERFACE.get(), new Item.Properties()));

    @SuppressWarnings("ConstantConditions")
    public static final RegistryObject<BlockEntityType<DommBlockEntity>> DOMM_BLOCK_ENTITY = BLOCK_ENTITIES.register("domm_interface", () -> BlockEntityType.Builder.of(DommBlockEntity::new, DOMM_INTERFACE.get()).build(null));

    public static final RegistryObject<MenuType<DommMenu>> DOMM_MENU = MENUS.register("domm_interface", () -> new MenuType<>((IContainerFactory<DommMenu>) (windowId, inv, data) -> new DommMenu(windowId, inv, data), FeatureFlags.VANILLA_SET));

    public static void register(IEventBus eventBus) {
        BLOCKS.register(eventBus);
        ITEMS.register(eventBus);
        BLOCK_ENTITIES.register(eventBus);
        MENUS.register(eventBus);
    }
}