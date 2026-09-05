package com.zzynes.flydrone.Radio;

import net.minecraft.client.renderer.ItemRenderer;
import net.minecraft.client.renderer.block.model.ItemTransforms;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import com.zzynes.flydrone.DRONE.FlyDroneMod;
import net.minecraft.ChatFormatting;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.renderer.ItemRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.block.model.ItemTransforms;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.client.renderer.entity.player.PlayerRenderer;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.client.extensions.common.IClientItemExtensions;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkEvent;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.PacketDistributor;
import net.minecraftforge.network.simple.SimpleChannel;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;
import net.minecraftforge.server.ServerLifecycleHooks;
import org.lwjgl.glfw.GLFW;
import software.bernie.geckolib.animatable.GeoItem;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.model.GeoModel;
import software.bernie.geckolib.renderer.GeoItemRenderer;
import software.bernie.geckolib.util.GeckoLibUtil;

import javax.annotation.Nullable;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.UUID;
import java.util.function.Consumer;
import java.util.function.Supplier;

public class RadioMod {

    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, FlyDroneMod.MOD_ID);

    public static final RegistryObject<Item> RADIO = ITEMS.register("radio",
            () -> new RadioItem(new Item.Properties().stacksTo(1)));

    public static final SimpleChannel CHANNEL = NetworkRegistry.newSimpleChannel(
            new ResourceLocation(FlyDroneMod.MOD_ID, "radio"), () -> "1", "1"::equals, "1"::equals);

    public static void init(IEventBus modBus) {
        ITEMS.register(modBus);

        CHANNEL.messageBuilder(SetFreqPacket.class, 0, NetworkDirection.PLAY_TO_SERVER)
                .encoder(SetFreqPacket::encode).decoder(SetFreqPacket::decode)
                .consumerMainThread(SetFreqPacket::handle).add();

        CHANNEL.messageBuilder(BodySyncPacket.class, 1, NetworkDirection.PLAY_TO_CLIENT)
                .encoder(BodySyncPacket::encode).decoder(BodySyncPacket::decode)
                .consumerMainThread(BodySyncPacket::handle).add();

        modBus.addListener(RadioMod::onRegisterKeys);
        modBus.addListener(RadioMod::onClientSetup);

        MinecraftForge.EVENT_BUS.register(new RadioEvents());
    }

    private static void onRegisterKeys(RegisterKeyMappingsEvent event) {
        event.register(RadioKeyHandler.KEY);
    }

    private static void onClientSetup(FMLClientSetupEvent event) {
        event.enqueueWork(() -> {
            for (EntityRenderer<? extends Player> r :
                    Minecraft.getInstance().getEntityRenderDispatcher().getSkinMap().values()) {
                if (r instanceof PlayerRenderer pr) {
                    pr.addLayer(new RadioChestLayer(pr));
                }
            }
        });
    }

    public static ItemStack findRadioOnBody(Player player) {
        ItemStack main = player.getMainHandItem();
        ItemStack off = player.getOffhandItem();
        for (ItemStack stack : player.getInventory().items) {
            if (stack.getItem() == RADIO.get() && stack != main && stack != off) return stack;
        }
        return null;
    }

    public static class RadioItem extends Item implements GeoItem {

        private static final Random RANDOM = new Random();

        public RadioItem(Properties properties) {
            super(properties);
        }

        public static int getFrequency(ItemStack stack) {
            CompoundTag tag = stack.getOrCreateTag();
            if (!tag.contains("Frequency")) {
                tag.putInt("Frequency", 100 + RANDOM.nextInt(900));
            }
            return tag.getInt("Frequency");
        }

        @Override
        public void appendHoverText(ItemStack stack, @Nullable Level level, List<Component> tooltip, TooltipFlag flag) {
            tooltip.add(Component.literal(ChatFormatting.GREEN + "Частота: " + getFrequency(stack)));
        }

        @Override
        public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        }

        @Override
        public AnimatableInstanceCache getAnimatableInstanceCache() {
            return GeckoLibUtil.createInstanceCache(this);
        }

        @Override
        public void initializeClient(Consumer<IClientItemExtensions> consumer) {
            consumer.accept(new IClientItemExtensions() {
                @Override
                public ItemRenderer getCustomRenderer() {
                    return RadioItemRenderer.INSTANCE;
                }
            });
        }
    }

    public static class RadioItemModel extends GeoModel<RadioItem> {
        @Override
        public ResourceLocation getModelResource(RadioItem object) {
            return new ResourceLocation("fly_drone", "geo/radio.geo.json");
        }

        @Override
        public ResourceLocation getTextureResource(RadioItem object) {
            return new ResourceLocation("fly_drone", "textures/item/radio_texture.png");
        }

        @Override
        public ResourceLocation getAnimationResource(RadioItem animatable) {
            return new ResourceLocation("fly_drone", "animations/radio.animation.json");
        }
    }

    public static class RadioItemRenderer extends GeoItemRenderer<RadioItem> {
        public static final RadioItemRenderer INSTANCE = new RadioItemRenderer();

        public RadioItemRenderer() {
            super(new RadioItemModel());
        }
    }

    public static class RadioKeyHandler {
        public static final KeyMapping KEY =
                new KeyMapping("key.fly_drone.radio_menu", GLFW.GLFW_KEY_Z, "key.categories.fly_drone");
    }

    public static class RadioScreen extends Screen {

        private static final ResourceLocation GUI =
                new ResourceLocation("fly_drone", "textures/gui/radio.png");

        private final int startFreq;
        private final StringBuilder input = new StringBuilder();

        public RadioScreen(ItemStack stack) {
            super(Component.literal("РАЦИЯ"));
            this.startFreq = RadioItem.getFrequency(stack);
        }

        @Override
        public boolean charTyped(char chr, int modifiers) {
            if (chr >= '0' && chr <= '9' && input.length() < 3) input.append(chr);
            return true;
        }

        @Override
        public boolean keyPressed(int keyCode, int scanCode, int modifiers) {
            if (keyCode == 259 && input.length() > 0) {
                input.deleteCharAt(input.length() - 1);
                return true;
            }
            return super.keyPressed(keyCode, scanCode, modifiers);
        }

        @Override
        public void onClose() {
            if (input.length() > 0) {
                int freq = Integer.parseInt(input.toString());
                if (freq >= 100 && freq <= 999) {
                    CHANNEL.sendToServer(new SetFreqPacket(freq));
                }
            }
            super.onClose();
        }

        @Override
        public void render(GuiGraphics g, int mouseX, int mouseY, float partialTick) {
            renderBackground(g);
            g.blit(GUI, 0, 0, this.width, this.height, 0, 0, 1920, 1080, 1920, 1080);

            float sx = this.width / 1920f;
            float sy = this.height / 1080f;
            int rx = (int) (807 * sx);
            int ry = (int) (264 * sy);
            int rw = (int) (404 * sx);
            int rh = (int) (180 * sy);

            String text = input.length() > 0 ? input.toString() : String.valueOf(startFreq);

            PoseStack pose = g.pose();
            pose.pushPose();
            float scale = (rh * 0.55f) / 8f;
            int textWidth = this.font.width(text);
            if (textWidth > 0) scale = Math.min(scale, (rw * 0.9f) / textWidth);
            pose.translate(rx + rw / 2f, ry + rh / 2f, 0);
            pose.scale(scale, scale, 1);
            g.drawCenteredString(this.font, text, 0, -4, 0x55FF55);
            pose.popPose();

            super.render(g, mouseX, mouseY, partialTick);
        }

        @Override
        public boolean isPauseScreen() {
            return false;
        }
    }

    public static class RadioChestLayer
            extends RenderLayer<AbstractClientPlayer, PlayerModel<AbstractClientPlayer>> {

        public static final Set<UUID> PLAYERS_WITH_RADIO =
                Collections.synchronizedSet(new HashSet<>());

        public static float OFF_X = 0.0f;
        public static float OFF_Y = 0.375f;
        public static float OFF_Z = 0.19f;
        public static float ROT_Y = 0.0f;
        public static float SCALE = 1.0f;

        public RadioChestLayer(RenderLayerParent<AbstractClientPlayer, PlayerModel<AbstractClientPlayer>> renderer) {
            super(renderer);
        }

        @Override
        public void render(PoseStack poseStack, MultiBufferSource buffer, int packedLight,
                           AbstractClientPlayer player, float limbSwing, float limbSwingAmount,
                           float partialTick, float ageInTicks, float netHeadYaw, float headPitch) {
            if (player.isInvisible()) return;

            ItemStack radio;
            if (player == Minecraft.getInstance().player) {
                radio = findRadioOnBody(player);
            } else {
                if (!PLAYERS_WITH_RADIO.contains(player.getUUID())) return;
                radio = new ItemStack(RADIO.get());
            }
            if (radio == null) return;

            poseStack.pushPose();
            getParentModel().body.translateAndRotate(poseStack);
            poseStack.translate(OFF_X, OFF_Y, OFF_Z);
            poseStack.mulPose(Axis.YP.rotationDegrees(ROT_Y));
            poseStack.scale(SCALE, SCALE, SCALE);

            RadioItemRenderer.INSTANCE.render(radio, ItemTransforms.TransformType.NONE, false,
                    poseStack, buffer, packedLight, OverlayTexture.NO_OVERLAY, null);

            poseStack.popPose();
        }
    }

    public static class SetFreqPacket {
        private final int freq;

        public SetFreqPacket(int freq) {
            this.freq = freq;
        }

        public static void encode(SetFreqPacket p, FriendlyByteBuf buf) {
            buf.writeVarInt(p.freq);
        }

        public static SetFreqPacket decode(FriendlyByteBuf buf) {
            return new SetFreqPacket(buf.readVarInt());
        }

        public static void handle(SetFreqPacket p, Supplier<NetworkEvent.Context> ctx) {
            ctx.get().enqueueWork(() -> {
                ServerPlayer player = ctx.get().getSender();
                if (player == null) return;
                if (p.freq < 100 || p.freq > 999) return;
                ItemStack stack = player.getMainHandItem();
                if (stack.getItem() == RADIO.get()) {
                    stack.getOrCreateTag().putInt("Frequency", p.freq);
                }
            });
            ctx.get().setPacketHandled(true);
        }
    }

    public static class BodySyncPacket {
        private final UUID playerId;
        private final boolean hasRadio;

        public BodySyncPacket(UUID playerId, boolean hasRadio) {
            this.playerId = playerId;
            this.hasRadio = hasRadio;
        }

        public static void encode(BodySyncPacket p, FriendlyByteBuf buf) {
            buf.writeUUID(p.playerId);
            buf.writeBoolean(p.hasRadio);
        }

        public static BodySyncPacket decode(FriendlyByteBuf buf) {
            return new BodySyncPacket(buf.readUUID(), buf.readBoolean());
        }

        public static void handle(BodySyncPacket p, Supplier<NetworkEvent.Context> ctx) {
            ctx.get().enqueueWork(() -> {
                if (p.hasRadio) RadioChestLayer.PLAYERS_WITH_RADIO.add(p.playerId);
                else RadioChestLayer.PLAYERS_WITH_RADIO.remove(p.playerId);
            });
            ctx.get().setPacketHandled(true);
        }
    }

    public static class RadioEvents {

        private static final Map<UUID, Boolean> STATE = new HashMap<>();
        private static int tickCounter = 0;

        @SubscribeEvent
        public void onClientTick(TickEvent.ClientTickEvent event) {
            if (event.phase != TickEvent.Phase.END) return;
            Minecraft mc = Minecraft.getInstance();
            if (mc.player == null || mc.screen != null) return;
            if (RadioKeyHandler.KEY.consumeClick()) {
                ItemStack stack = mc.player.getMainHandItem();
                if (stack.getItem() == RADIO.get()) {
                    mc.setScreen(new RadioScreen(stack));
                }
            }
        }

        @SubscribeEvent
        public void onServerTick(TickEvent.ServerTickEvent event) {
            if (event.phase != TickEvent.Phase.END) return;
            if (++tickCounter % 20 != 0) return;
            MinecraftServer server = ServerLifecycleHooks.getCurrentServer();
            if (server == null) return;
            for (ServerPlayer player : server.getPlayerList().getPlayers()) {
                boolean has = findRadioOnBody(player) != null;
                Boolean prev = STATE.get(player.getUUID());
                if (prev == null || prev != has) {
                    STATE.put(player.getUUID(), has);
                    CHANNEL.send(PacketDistributor.ALL.noArg(),
                            new BodySyncPacket(player.getUUID(), has));
                }
            }
        }

        @SubscribeEvent
        public void onLogout(PlayerEvent.PlayerLoggedOutEvent event) {
            STATE.remove(event.getEntity().getUUID());
        }
    }
}